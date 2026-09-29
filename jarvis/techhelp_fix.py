"""Tech helper, fixing things: step-by-step troubleshooting guides, keyboard shortcut cheat sheets, a jargon
glossary and a which-cable-or-charger guide. Ticked steps are kept in techhelp-progress.json in the memory folder;
everything else is built in and nothing goes online.
"""

import re

import homestore as hs
import screen
import techhelp_data as data
import techhelp_ref as ref
import techhelp_store as store
from config import Settings

ACTIONS = ["guide_list", "guide_start", "guide_tick", "guide_reset", "shortcuts", "jargon", "cable_guide"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "techhelp_fix",
        "description": "Fix tech problems and explain tech. guide_list, guide_start (topic: Wi-Fi not working, "
                       "printer offline, slow PC, no sound, Bluetooth won't pair, phone storage full, iPhone backup; "
                       "pops up a clickable checklist, then read out only the current step and wait), guide_tick "
                       "(user did a step: step number, or leave out for the current one; done false unticks) and "
                       "guide_reset. shortcuts (Windows keyboard shortcuts by app: windows, explorer, browser, word, "
                       "excel, text, powerpoint, vscode, or search a word like 'screenshot'). jargon (explain a "
                       "tech word in plain English; leave term out for the whole glossary). cable_guide (which "
                       "cable or charger for a device or need, e.g. 'iPhone 15', 'monitor 4K').",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "topic": {"type": "string", "description": "guide_*: the problem, e.g. 'wifi', 'printer'."},
                "step": {"type": "integer", "description": "guide_tick: step number from the list."},
                "done": {"type": "boolean", "description": "guide_tick: false unticks."},
                "app": {"type": "string", "description": "shortcuts: the app."},
                "search": {"type": "string", "description": "shortcuts: a word to look for in every app."},
                "term": {"type": "string", "description": "jargon: the word."},
                "query": {"type": "string", "description": "cable_guide: the device or need."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"techhelp_fix"}


# ---- guides --------------------------------------------------------------------------------

def _guide(topic) -> tuple[str, str, list]:
    text = hs.need(topic, "problem").lower()
    for key, (title, steps) in data.GUIDES.items():
        if text in (key, title.lower()):
            return key, title, steps
    for key, words in data.ALIASES.items():
        if any(w in text for w in words):
            return key, *data.GUIDES[key]
    raise ValueError("I haven't got a guide for that. I have: " + ", ".join(t for t, _ in data.GUIDES.values()) + ".")


def _about(title: str) -> str:
    return f"the {title} guide"


def guide_list(settings: Settings) -> screen.Shown:
    items = []
    for key, (title, steps) in data.GUIDES.items():
        done = len(store.done_steps(settings, f"guide-{key}", len(steps)))
        note = f" ({done} of {len(steps)} done)" if done else ""
        items.append({"label": title + note, "say": f"Walk me through the {title} guide."})
    return screen.Shown("Pick a problem and I'll walk you through it.",
                        screen.card("list", "Fix a tech problem", "techhelp-guides", items=items))


def guide_start(settings: Settings, args: dict) -> screen.Shown:
    key, title, steps = _guide(args.get("topic"))
    return store.show(settings, f"guide-{key}", title, steps, _about(title))


def guide_tick(settings: Settings, args: dict) -> screen.Shown:
    key, title, steps = _guide(args.get("topic"))
    return store.tick(settings, f"guide-{key}", title, steps, _about(title), args.get("step"), args.get("done") is not False)


def guide_reset(settings: Settings, args: dict) -> screen.Shown:
    key, title, steps = _guide(args.get("topic"))
    return store.reset(settings, f"guide-{key}", title, steps, _about(title))


# ---- shortcuts, jargon, cables ---------------------------------------------------------------

def shortcuts(args: dict) -> screen.Shown:
    search = hs.clean(args.get("search")).lower()
    app = hs.clean(args.get("app")).lower()
    if search:
        rows = [[keys, what, name] for name, lines in ref.SHORTCUTS.values() for keys, what in lines
                if search in what.lower() or search in keys.lower()]
        if not rows:
            raise ValueError(f"I can't find a shortcut for {search}.")
        return screen.Shown(f"Found {len(rows)} shortcuts for {search}.", screen.card(
            "table", f"Shortcuts: {search}", f"techhelp-shortcuts-{search}", columns=["Keys", "Does", "App"], rows=rows))
    key = next((k for k, words in ref.SHORTCUT_WORDS.items() if app == k or app in words or (app and app in ref.SHORTCUTS[k][0].lower())), None)
    if key is None:
        items = [{"label": name, "say": f"Show me the {name} keyboard shortcuts."} for name, _ in ref.SHORTCUTS.values()]
        return screen.Shown("Which app's shortcuts do you want?", screen.card(
            "list", "Keyboard shortcuts", "techhelp-shortcut-apps", items=items))
    name, lines = ref.SHORTCUTS[key]
    return screen.Shown(f"Here are the {name} shortcuts.", screen.card(
        "table", f"{name} shortcuts", f"techhelp-shortcuts-{key}", columns=["Keys", "Does"], rows=[list(x) for x in lines]))


def jargon(args: dict) -> screen.Shown:
    term = hs.clean(args.get("term")).lower()
    if not term:
        rows = [[k.title() if len(k) > 4 else k.upper(), v] for k, v in sorted(ref.JARGON.items())]
        return screen.Shown(f"{len(rows)} tech words explained on screen.", screen.card(
            "table", "Tech jargon", "techhelp-jargon", columns=["Word", "In plain English"], rows=rows))
    found = term if term in ref.JARGON else next(
        (k for k in sorted(ref.JARGON, key=len, reverse=True) if re.search(rf"(?<![\w-]){re.escape(k)}(?![\w-])", term)),
        next((k for k in ref.JARGON if term in k), None))
    if found is None:
        raise ValueError(f"I haven't got {term} in my glossary; I'll explain it from what I know.")
    return screen.Shown(f"{found}: {ref.JARGON[found]}", screen.card(
        "text", found.title() if len(found) > 4 else found.upper(), f"techhelp-jargon-{found}", text=ref.JARGON[found],
        buttons=[{"label": "All jargon", "say": "Show me the tech jargon glossary."}]))


def cable_guide(args: dict) -> screen.Shown:
    query = hs.clean(args.get("query"), 120).lower()
    scored = sorted(((sum(w in query for w in words), device, cable, tip) for words, device, cable, tip in ref.CABLES),
                    key=lambda r: -r[0])
    hits = [r for r in scored if r[0]][:3]
    if not hits:
        return screen.Shown("Here's how to tell the common plugs apart.", screen.card(
            "table", "Which plug is which", "techhelp-connectors", columns=["Plug", "Looks like", "Used for"],
            rows=[list(c) for c in ref.CONNECTORS]))
    top = hits[0]
    return screen.Shown(f"For {top[1]}: {top[2]}. {top[3]}", screen.card(
        "table", "Which cable or charger", "techhelp-cables", columns=["For", "Use", "Tip"],
        rows=[[d, c, t] for _, d, c, t in hits]))


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "guide_list":
        return guide_list(settings)
    if action == "guide_start":
        return guide_start(settings, args)
    if action == "guide_tick":
        return guide_tick(settings, args)
    if action == "guide_reset":
        return guide_reset(settings, args)
    if action == "shortcuts":
        return shortcuts(args)
    if action == "jargon":
        return jargon(args)
    if action == "cable_guide":
        return cable_guide(args)
    raise ValueError(f"Unknown action {action}.")
