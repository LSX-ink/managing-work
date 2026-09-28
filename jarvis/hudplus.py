"""HUD secrets: Alfred drives the HUD page itself by voice.

Tidy, shrink or close the pop-up windows, focus mode, the screensaver, the colour theme, zoom, a clean screen
without the side panels, the keyboard shortcuts, a "what can you do" list, and sticky notes on the HUD.

Every action returns a "hud" card; frontend/hudplus.js performs it on the page instead of drawing a window.
Sticky notes made by voice are kept in memory/sticky-notes.json; notes made on the page live in that browser.
"""

import json
import time
import uuid

import memory
import screen
from config import Settings

screen.EXTRA_KINDS.add("hud")

THEMES = ("hud-stars", "hud-gold", "hud", "hud-purple", "hud-red", "hud-green")
COLOURS = ("yellow", "pink", "blue", "green", "white")
MAX_NOTES = 50
MAX_NOTE = 500

ACTIONS = ("tidy_windows", "close_windows", "minimise_windows", "focus_mode", "screensaver", "theme", "zoom",
           "clean_screen", "shortcuts", "palette", "help", "note_add", "note_list", "note_remove", "note_clear")

HELP = [
    ("Add call the bank to my to-do list", "Add call the bank to my to-do list."),
    ("What's on my to-do list?", "What's on my to-do list?"),
    ("How much have I spent this month?", "How much have I spent this month?"),
    ("How are my streaks?", "How are my streaks?"),
    ("What's the weather this week?", "What's the weather for the next few days?"),
    ("What's in the news?", "What's in the news?"),
    ("Do I need an umbrella?", "Do I need an umbrella this afternoon?"),
    ("What time is it in Tokyo?", "What time is it in Tokyo?"),
    ("How many days until Christmas?", "How many days until Christmas?"),
    ("What's 15% of 80?", "What's 15% of 80?"),
    ("How many kilometres is 26.2 miles?", "How many kilometres is 26.2 miles?"),
    ("What are we eating this week?", "What are we eating this week?"),
    ("What's in the pantry?", "What's in the pantry?"),
    ("Quiz me on some French", "Quiz me on some French."),
    ("Give me a trivia question", "Give me a trivia question."),
    ("Tell me a joke", "Tell me a joke."),
    ("What does ubiquitous mean?", "What does ubiquitous mean?"),
    ("Take a screenshot", "Take a screenshot."),
    ("Tidy my windows", "Tidy my windows."),
    ("Add a sticky note", "Add a sticky note: buy milk."),
]


def tool_definitions() -> list[dict]:
    return [{
        "name": "hud_control",
        "description": "Control the Alfred HUD screen itself. tidy_windows tiles the pop-up windows in a grid; "
                       "close_windows closes all pop-ups (pinned ones stay); minimise_windows shrinks them all; "
                       "focus_mode dims everything but the chat and pop-ups; screensaver (ambient clock, 'on' "
                       "starts it now, 'off' stops it coming on, minutes sets the idle time); theme switches the "
                       "colours live (stars, gold...); zoom makes the HUD bigger or smaller; clean_screen hides or "
                       "shows the side panels; shortcuts shows the keyboard shortcuts; palette opens the command "
                       "palette; help shows 'what can you do' examples; note_add, note_list, note_remove and "
                       "note_clear handle sticky notes on the HUD. note_remove and note_clear delete notes: set "
                       "confirmed true only after the user has confirmed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "on": {"type": "boolean", "description": "focus_mode, screensaver, clean_screen: on or off. "
                                                         "Leave out to toggle."},
                "minutes": {"type": "integer", "description": "screensaver: idle minutes before it starts, 1-120."},
                "theme": {"type": "string", "enum": [*THEMES, "toggle"],
                          "description": "theme: hud-stars is black and white, hud-gold amber, hud the original blue; "
                                         "toggle swaps stars and gold."},
                "zoom": {"type": "string", "enum": ["bigger", "smaller", "reset"]},
                "text": {"type": "string", "description": "note_add: the note; note_remove: words in the note."},
                "colour": {"type": "string", "enum": list(COLOURS)},
                "confirmed": {"type": "boolean", "description": "note_remove, note_clear: true only after the "
                                                                "user confirmed."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"hud_control"}


def _hud(text: str, action: str, **data) -> screen.Shown:
    return screen.Shown(text, screen.card("hud", "HUD", "hud-control", data={"action": action, **data}))


def notes_path(settings: Settings):
    return memory.root(settings) / "sticky-notes.json"


def load_notes(settings: Settings) -> list[dict]:
    try:
        notes = json.loads(notes_path(settings).read_text(encoding="utf-8")).get("notes", [])
    except (OSError, ValueError, AttributeError):
        return []
    return [n for n in notes if isinstance(n, dict) and n.get("id") and n.get("text")]


def save_notes(settings: Settings, notes: list[dict]) -> None:
    path = notes_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"notes": notes}, indent=1), encoding="utf-8")


def _toggle_word(on, name: str) -> str:
    return f"{name} {'on' if on else 'off'}." if on is not None else f"Toggled {name.lower()}."


def note_add(settings: Settings, text: str, colour: str) -> screen.Shown:
    text = " ".join(str(text or "").split())[:MAX_NOTE]
    if not text:
        raise ValueError("What should the note say?")
    notes = load_notes(settings)
    if len(notes) >= MAX_NOTES:
        raise ValueError(f"There are already {MAX_NOTES} notes; clear some first.")
    note = {"id": uuid.uuid4().hex[:10], "text": text, "colour": colour if colour in COLOURS else "yellow",
            "created": int(time.time())}
    save_notes(settings, notes + [note])
    return _hud("Stuck a note on the screen.", "note_add", note=note)


def note_list(settings: Settings) -> screen.Shown:
    notes = load_notes(settings)
    said = "; ".join(n["text"] for n in notes)
    text = f"Notes I've added: {said}." if notes else "I haven't added any notes by voice."
    return _hud(text + " All your sticky notes are on the screen.", "notes_show")


def note_remove(settings: Settings, text: str, confirmed: bool) -> screen.Shown | str:
    want = str(text or "").strip().lower()
    if not want:
        raise ValueError("Which note? Tell me some words from it.")
    if not confirmed:
        return f"Remove the sticky notes that mention '{want}'? Say yes to confirm."
    notes = load_notes(settings)
    keep = [n for n in notes if want not in n["text"].lower()]
    save_notes(settings, keep)
    return _hud(f"Removed the notes mentioning '{want}'.", "note_remove", match=want)


def note_clear(settings: Settings, confirmed: bool) -> screen.Shown | str:
    if not confirmed:
        return "Clear every sticky note from the screen? Say yes to confirm."
    save_notes(settings, [])
    return _hud("Cleared all the sticky notes.", "note_clear")


def help_card() -> screen.Shown:
    items = [{"label": label, "say": say} for label, say in HELP]
    return screen.Shown("Here are some things you can ask me; click one to try it.", screen.card(
        "list", "What I can do", "hud-help", items=items,
        text="Click a line to ask it. Press Ctrl+K for more, or ? for keyboard shortcuts.",
        buttons=[{"label": "Keyboard shortcuts", "say": "Show the HUD keyboard shortcuts."}]))


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    on = args.get("on")
    on = bool(on) if on is not None else None
    if action == "tidy_windows":
        return _hud("Tidied the windows.", "tidy")
    if action == "close_windows":
        return _hud("Closed the windows; pinned ones stay.", "close_all")
    if action == "minimise_windows":
        return _hud("Shrunk all the windows.", "minimise_all")
    if action == "focus_mode":
        return _hud(_toggle_word(on, "Focus mode"), "focus", on=on)
    if action == "clean_screen":
        return _hud("Side panels hidden." if on else "Side panels back." if on is False
                    else "Toggled the side panels.", "clean", on=on)
    if action == "screensaver":
        minutes = args.get("minutes")
        if minutes is not None:
            minutes = min(max(int(minutes), 1), 120)
            return _hud(f"The screensaver comes on after {minutes} idle minutes.", "screensaver", on=on,
                        minutes=minutes)
        if on is False:
            return _hud("Screensaver off; it won't come on by itself.", "screensaver", on=False)
        return _hud("Screensaver on. Press any key to come back.", "screensaver", on=True)
    if action == "theme":
        theme = args.get("theme") or "toggle"
        if theme not in (*THEMES, "toggle"):
            raise ValueError("Pick hud-stars, hud-gold, hud, hud-purple, hud-red or hud-green.")
        return _hud("Swapped the colours." if theme == "toggle" else f"Switched to the {theme} theme.",
                    "theme", theme=theme)
    if action == "zoom":
        way = args.get("zoom") or "bigger"
        if way not in ("bigger", "smaller", "reset"):
            raise ValueError("Say bigger, smaller or reset.")
        return _hud("Back to normal size." if way == "reset" else f"Made the HUD {way}.", "zoom", zoom=way)
    if action == "shortcuts":
        return _hud("The keyboard shortcuts are on the screen.", "shortcuts")
    if action == "palette":
        return _hud("The command palette is open; type or pick a request.", "palette")
    if action == "help":
        return help_card()
    if action == "note_add":
        return note_add(settings, args.get("text"), args.get("colour") or "yellow")
    if action == "note_list":
        return note_list(settings)
    if action == "note_remove":
        return note_remove(settings, args.get("text"), bool(args.get("confirmed")))
    if action == "note_clear":
        return note_clear(settings, bool(args.get("confirmed")))
    raise ValueError(f"Unknown HUD action {action}.")
