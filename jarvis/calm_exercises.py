"""Calm exercises that pop up on the Alfred screen: animated breathing (box, 4-7-8, coherent, physiological sigh or your
own rhythm), a meditation timer with bells, guided scripts read step by step, a calm-down menu and the support numbers.

Pop-ups are "calm-breathe", "calm-bells" and "calm-guide" (frontend/popup-calm.js); sounds are made by the page with Web
Audio. Nothing here is medical advice.
"""

import calm_data as data
import calm_store as store
import screen
from config import Settings

screen.EXTRA_KINDS.update({"calm-breathe", "calm-bells", "calm-guide"})
ACTIONS = ["breathe", "breathing_custom", "breathing_patterns", "meditate", "guide", "guide_list", "calm_menu", "support"]
NAMES = {"calm_exercises"}


def _pick(value, aliases: dict, table: dict, what: str) -> str:
    key = store.clean(value).lower().replace("_", " ")
    key = aliases.get(key) or aliases.get(key.replace(" ", "-")) or key.replace(" ", "_")
    if key not in table:
        raise ValueError(f"I know {', '.join(table)} {what}.".replace("_", " "))
    return key


def _breathe_card(title: str, phases: list, blurb: str, mins: float, tone: bool, card_id: str) -> screen.Shown:
    say = f"Log {mins:g} mindful minutes of breathing"
    card = screen.card("calm-breathe", title, card_id, buttons=[{"label": "Log it", "say": say}],
                       data={"phases": [{"label": p, "seconds": s} for p, s in phases], "minutes": mins,
                             "blurb": blurb, "tone": tone})
    return screen.Shown(f"{title} for {mins:g} minutes. Follow the circle; {blurb.split('.')[0].lower()}.", card)


def breathe(args: dict) -> screen.Shown:
    key = _pick(args.get("pattern") or "box", data.BREATHING_ALIASES, data.BREATHING, "breathing")
    title, phases, blurb = data.BREATHING[key]
    return _breathe_card(title, phases, blurb, store.minutes(args.get("minutes") or 3, high=30),
                         args.get("tone") is not False, f"calm-breathe-{key}")


def breathing_custom(args: dict) -> screen.Shown:
    phases = []
    for label, field in (("Breathe in", "inhale"), ("Hold", "hold_in"), ("Breathe out", "exhale"), ("Hold", "hold_out")):
        seconds = float(store.hs.number(args.get(field) or 0, field.replace("_", " "), 0, 20))
        if seconds:
            phases.append((label, seconds))
    if not any(p[0] == "Breathe in" for p in phases) or not any(p[0] == "Breathe out" for p in phases):
        raise ValueError("Give at least the seconds to breathe in (inhale) and out (exhale).")
    blurb = ", ".join(f"{p.lower()} {s:g}" for p, s in phases) + "."
    return _breathe_card("Your breathing", phases, blurb[0].upper() + blurb[1:],
                         store.minutes(args.get("minutes") or 3, high=30), args.get("tone") is not False,
                         "calm-breathe-custom")


def breathing_patterns() -> screen.Shown:
    rows = [[title, " / ".join(f"{s:g}" for _, s in phases), blurb] for title, phases, blurb in data.BREATHING.values()]
    card = screen.card("table", "Breathing exercises", "calm-patterns", columns=["Name", "Seconds", "About"], rows=rows,
                       buttons=[{"label": title, "say": f"Start {title.lower()}"} for title, *_ in data.BREATHING.values()])
    return screen.Shown("I know box, 4-7-8, coherent and physiological sigh breathing; they're on the screen.", card)


def meditate(args: dict) -> screen.Shown:
    mins = store.minutes(args.get("minutes") or 10, high=180)
    interval = store.hs.number(args.get("interval_minutes") or 0, "interval", 0, 180)
    if interval and interval >= mins:
        raise ValueError("The interval bell needs to be shorter than the whole sit.")
    card = screen.card("calm-bells", "Meditation timer", "calm-bells",
                       buttons=[{"label": "Log it", "say": f"Log {mins:g} mindful minutes of meditation"}],
                       data={"minutes": mins, "interval": interval, "start_bell": args.get("start_bell") is not False,
                             "end_bell": args.get("end_bell") is not False})
    every = f", with a soft bell every {interval:g} minutes" if interval else ""
    return screen.Shown(f"A {mins:g} minute meditation timer{every}. Press Begin when you're settled.", card)


def guide(args: dict) -> screen.Shown:
    key = _pick(args.get("script"), data.GUIDE_ALIASES, data.GUIDES, "guides")
    title, steps = data.GUIDES[key]
    card = screen.card("calm-guide", title, f"calm-guide-{key}",
                       data={"steps": [{"text": t, "pause": p} for t, p in steps]})
    return screen.Shown(f"{title}, {len(steps)} steps. Press Begin and I'll take you through it slowly.", card)


def guide_list() -> screen.Shown:
    items = [{"label": title, "say": f"Guide me through {title.lower()}"} for title, _ in data.GUIDES.values()]
    card = screen.card("list", "Guided calm", "calm-guides", items=items)
    return screen.Shown("I can guide you through a body scan, grounding, loving-kindness, muscle relaxation or a sleepy "
                        "wind-down. Pick one on the screen.", card)


def calm_menu(args: dict) -> screen.Shown:
    feeling = store.clean(args.get("feeling")).lower()
    if store.in_crisis(feeling, args.get("text")):
        return support()
    if not feeling:
        items = [{"label": f.title(), "say": f"I'm feeling {f}, what can I do to calm down?"} for f in data.CALM_MENU]
        card = screen.card("list", "How are you feeling?", "calm-menu", items=items)
        return screen.Shown("How are you feeling? Pick one and I'll give you some quick ideas.", card)
    key = data.FEELING_ALIASES.get(feeling, feeling)
    if key not in data.CALM_MENU:
        raise ValueError(f"I have ideas for feeling {', '.join(data.CALM_MENU)}.")
    ideas = data.CALM_MENU[key]
    card = screen.card("list", f"Feeling {key}", f"calm-menu-{key}", items=[{"label": i} for i in ideas],
                       buttons=[{"label": "Breathe with me", "say": "Start physiological sigh breathing"},
                                {"label": "Ground me", "say": "Guide me through 5-4-3-2-1 grounding"}])
    return screen.Shown(f"Feeling {key}? Try this: {ideas[0]} More ideas are on the screen. {store.SAFETY}", card)


def support() -> screen.Shown:
    card = screen.card("text", "You're not alone", "calm-support",
                       text="Samaritans: 116 123 (free, 24 hours)\nNHS 111: for urgent help that isn't an emergency\n"
                            "999: if you or someone else is in immediate danger")
    return screen.Shown(store.SUPPORT, card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "calm_exercises",
        "description": "Calm and mindfulness pop-ups. breathe (pattern box, 4-7-8, coherent for 5.5 seconds, or "
                       "physiological sigh; minutes; tone false for silent), breathing_custom (inhale, hold_in, exhale, "
                       "hold_out seconds), breathing_patterns, meditate (meditation timer with start, interval and end "
                       "bells: minutes, interval_minutes), guide (script body_scan, grounding for 5-4-3-2-1, "
                       "loving_kindness, muscle_relaxation, wind_down; read step by step with pauses), guide_list, "
                       "calm_menu (feeling anxious, angry, overwhelmed, restless, sad, tired, lonely; empty lists them), "
                       "support (Samaritans 116 123 and NHS 111). Never medical advice; if someone mentions self-harm or "
                       "crisis, use support at once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "pattern": {"type": "string", "description": "box, 4-7-8, coherent or sigh."},
                "minutes": {"type": "number"},
                "tone": {"type": "boolean", "description": "Soft tone with the breathing; false for silent."},
                "inhale": {"type": "number"}, "hold_in": {"type": "number"},
                "exhale": {"type": "number"}, "hold_out": {"type": "number"},
                "interval_minutes": {"type": "number", "description": "Bell every this many minutes; 0 for none."},
                "start_bell": {"type": "boolean"}, "end_bell": {"type": "boolean"},
                "script": {"type": "string"},
                "feeling": {"type": "string"},
                "text": {"type": "string", "description": "Anything the user said about how they feel."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if store.in_crisis(args.get("text"), args.get("feeling")):
        return support()
    if action == "breathe":
        return breathe(args)
    if action == "breathing_custom":
        return breathing_custom(args)
    if action == "breathing_patterns":
        return breathing_patterns()
    if action == "meditate":
        return meditate(args)
    if action == "guide":
        return guide(args)
    if action == "guide_list":
        return guide_list()
    if action == "calm_menu":
        return calm_menu(args)
    if action == "support":
        return support()
    raise ValueError(f"Unknown action {action}.")
