"""Widgets: small interactive tools that pop up on the Alfred screen and run in the page.

Calculator, unit converter, sketch pad, notepad, stopwatch, countdown, pomodoro, world clocks, month calendar,
dice, coin flip, colour picker, metronome, ambient noise, breathing exercise, typing test and a picker wheel.
This module only checks the request and builds the card; frontend/popup-widgets.js draws and runs each widget.
The sketch pad and notepad save into a memory folder through the page's own /memory endpoints.
"""

import re
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import memory
import screen
from config import Settings
from dates import CITY_ZONES

KIND = "widget"
screen.EXTRA_KINDS.add(KIND)

WIDGETS = {
    "calculator": "Calculator", "unit_converter": "Unit converter", "sketch_pad": "Sketch pad",
    "notepad": "Notepad", "stopwatch": "Stopwatch", "countdown": "Countdown", "pomodoro": "Pomodoro",
    "world_clocks": "World clocks", "calendar": "Calendar", "dice": "Dice", "coin_flip": "Coin flip",
    "colour_picker": "Colour picker", "metronome": "Metronome", "ambient_sound": "Ambient sound",
    "breathing": "Breathing", "typing_test": "Typing test", "picker_wheel": "Picker wheel",
}
SPOKEN = {
    "calculator": "Here's a calculator.", "unit_converter": "Here's the unit converter.",
    "sketch_pad": "Here's a sketch pad.", "notepad": "Here's a notepad.", "stopwatch": "Here's a stopwatch.",
    "countdown": "Here's a countdown timer.", "pomodoro": "Here's a pomodoro timer.",
    "world_clocks": "Here are the world clocks.", "calendar": "Here's the calendar.", "dice": "Here are the dice.",
    "coin_flip": "Here's a coin to flip.", "colour_picker": "Here's a colour picker.",
    "metronome": "Here's a metronome.", "ambient_sound": "Here's the ambient sound player.",
    "breathing": "Here's a breathing exercise.", "typing_test": "Here's a typing test.",
    "picker_wheel": "Here's the picker wheel.",
}
CATEGORIES = ("length", "weight", "temperature", "volume")
SOUNDS = ("rain", "white", "pink", "brown")
PATTERNS = ("box", "4-7-8")
DICE_SIDES = (4, 6, 8, 10, 12, 20, 100)
DEFAULT_CITIES = ["London", "New York", "Tokyo", "Sydney"]
NOTE_TYPES = {".md", ".txt"}
MAX_NOTE = 50_000
MAX_OPTIONS = 20


def _folder_name(settings: Settings, which: str) -> str:
    """One of the six memory folders by name (any case); the pop-up saves into it by its position."""
    wanted = (which or "Ideas").strip().lower()
    for name in memory.names(settings):
        if name.lower() == wanted:
            return name
    raise ValueError(f"I can only save widgets into one of these folders: {', '.join(memory.names(settings))}.")


def _number(value, low: float, high: float, what: str) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"The {what} needs to be a number.") from None
    if not low <= n <= high:
        raise ValueError(f"The {what} must be between {low:g} and {high:g}.")
    return n


def zones(cities: list[str]) -> tuple[list[dict], list[str]]:
    """([{label, zone}], unknown names) for city names, countries in the dates list, or IANA zones."""
    found, unknown = [], []
    for city in cities[:12]:
        name = str(city).strip()
        zone = CITY_ZONES.get(name.lower())
        if not zone and "/" in name:
            try:
                zone = ZoneInfo(name.replace(" ", "_")).key
            except (ZoneInfoNotFoundError, ValueError):
                zone = None
        if zone:
            label = name.split("/")[-1].replace("_", " ")
            found.append({"label": label.title() if label.islower() else label, "zone": zone})
        elif name:
            unknown.append(name)
    return found, unknown


def parse_dice(text: str) -> dict:
    m = re.fullmatch(r"\s*(\d*)\s*d\s*(\d+)\s*", str(text or "").lower())
    if not m:
        raise ValueError("Say the dice like 2d6 or d20.")
    count, sides = int(m.group(1) or 1), int(m.group(2))
    if not 1 <= count <= 10 or sides not in DICE_SIDES:
        raise ValueError("I can roll 1 to 10 dice with 4, 6, 8, 10, 12, 20 or 100 sides.")
    return {"count": count, "sides": sides}


def open_note(settings: Settings, folder: str, filename: str) -> dict:
    path = screen.find_file(settings, folder, filename)
    if path.suffix.lower() not in NOTE_TYPES:
        raise ValueError(f"{path.name} isn't a text note.")
    top = path.resolve().relative_to(memory.root(settings).resolve()).parts[0]
    return {"title": path.stem, "text": path.read_text(encoding="utf-8", errors="replace")[:MAX_NOTE],
            "folder": _folder_name(settings, top) if top.lower() in {n.lower() for n in memory.names(settings)}
            else "Ideas"}


def widget_data(action: str, args: dict, settings: Settings, today: date) -> tuple[dict, str]:
    """(data for the pop-up, extra words for Alfred to say)."""
    data: dict = {"widget": action}
    said = ""
    if action == "calculator" and args.get("expression"):
        data["expression"] = str(args["expression"])[:120]
    elif action == "unit_converter":
        category = args.get("category") or "length"
        if category not in CATEGORIES:
            raise ValueError("I can convert length, weight, temperature or volume.")
        data["category"] = category
        if args.get("value") is not None:
            data["value"] = _number(args["value"], -1e12, 1e12, "value")
    elif action in ("sketch_pad", "notepad"):
        data["folder"] = _folder_name(settings, args.get("folder") or "Ideas")
        if action == "notepad" and args.get("note"):
            data.update(open_note(settings, args.get("folder") or "", args["note"]))
            said = f" I've opened {data['title']}."
        elif action == "notepad" and args.get("text"):
            data["text"] = str(args["text"])[:MAX_NOTE]
            data["title"] = str(args.get("title") or "")[:60]
    elif action == "countdown":
        seconds = _number(args.get("minutes") or 0, 0, 1440, "minutes") * 60 + \
            _number(args.get("seconds") or 0, 0, 86400, "seconds")
        data["seconds"] = int(seconds) or 300
        data["autostart"] = bool(seconds)
    elif action == "pomodoro":
        data["work"] = int(_number(args.get("minutes") or 25, 1, 180, "focus minutes"))
        data["rest"] = int(_number(args.get("break_minutes") or 5, 1, 60, "break minutes"))
    elif action == "world_clocks":
        data["clocks"], unknown = zones(args.get("cities") or DEFAULT_CITIES)
        if unknown:
            said = f" I don't know the time zone for {', '.join(unknown)}."
        if not data["clocks"]:
            raise ValueError(f"I don't know the time zone for {', '.join(unknown)}; try a big city nearby.")
    elif action == "calendar":
        month = str(args.get("month") or "").strip()
        if month and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            raise ValueError("Give the month as YYYY-MM.")
        year, mon = (int(month[:4]), int(month[5:])) if month else (today.year, today.month)
        data.update(year=year, month=mon)
    elif action == "dice":
        data.update(parse_dice(args.get("dice") or "1d6"))
    elif action == "colour_picker" and args.get("colour"):
        colour = str(args["colour"]).strip()
        if not re.fullmatch(r"#?[0-9a-fA-F]{6}", colour):
            raise ValueError("Give the colour as a hex code like #3fa9ff.")
        data["colour"] = "#" + colour.lstrip("#").lower()
    elif action == "metronome":
        data["bpm"] = int(_number(args.get("bpm") or 100, 30, 240, "tempo"))
    elif action == "ambient_sound":
        sound = args.get("sound") or "rain"
        if sound not in SOUNDS:
            raise ValueError("I can play rain, white, pink or brown noise.")
        data["sound"] = sound
        data["minutes"] = int(_number(args.get("minutes") or 0, 0, 480, "sleep timer minutes"))
    elif action == "breathing":
        pattern = args.get("pattern") or "box"
        if pattern not in PATTERNS:
            raise ValueError("I know box breathing and 4-7-8 breathing.")
        data["pattern"] = pattern
    elif action == "picker_wheel":
        options = [str(o).strip()[:40] for o in args.get("options") or [] if str(o).strip()]
        if len(options) > MAX_OPTIONS:
            raise ValueError(f"The wheel holds up to {MAX_OPTIONS} options.")
        data["options"] = options
    return data, said


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "open_widget",
        "description": "Pop an interactive widget up on the Alfred screen that the user works with themselves. "
                       "action: 'calculator' (optional expression); 'unit_converter' length/weight/temperature/"
                       "volume converter (category, value); 'sketch_pad' draw or doodle, saves a picture to "
                       "folder; 'notepad' write a note, saves to folder, or edit an existing note (note = its file "
                       "name); 'stopwatch' with laps; 'countdown' timer with a chime (minutes, seconds); "
                       "'pomodoro' focus timer (minutes, break_minutes); 'world_clocks' clocks for cities; "
                       "'calendar' month calendar (month YYYY-MM); 'dice' roller (dice like 2d6); 'coin_flip'; "
                       "'colour_picker' (colour hex); 'metronome' (bpm); 'ambient_sound' rain, white, pink or "
                       "brown noise to relax or sleep (sound, minutes = sleep timer); 'breathing' exercise "
                       "(pattern box or 4-7-8); 'typing_test' typing speed WPM test; 'picker_wheel' spin a wheel "
                       "to pick from options. Use when the user wants the widget, a pop-up or to do it themselves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(WIDGETS)},
                "expression": text,
                "category": {"type": "string", "enum": list(CATEGORIES)},
                "value": {"type": "number"},
                "folder": {"type": "string", "description": "Memory folder to save into, e.g. Ideas (default)."},
                "note": {"type": "string", "description": "notepad: an existing note's file name to open."},
                "title": text,
                "text": {"type": "string", "description": "notepad: starting text."},
                "minutes": {"type": "number"},
                "seconds": {"type": "number"},
                "break_minutes": {"type": "number"},
                "cities": {"type": "array", "items": text},
                "month": text,
                "dice": text,
                "colour": text,
                "bpm": {"type": "integer"},
                "sound": {"type": "string", "enum": list(SOUNDS)},
                "pattern": {"type": "string", "enum": list(PATTERNS)},
                "options": {"type": "array", "items": text},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"open_widget"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None) -> screen.Shown:
    action = args.get("action")
    if action not in WIDGETS:
        raise ValueError(f"I don't have a {action} widget.")
    data, said = widget_data(action, args, settings, today or date.today())
    card = screen.card(KIND, WIDGETS[action], f"widget-{action}", data=data)
    return screen.Shown(SPOKEN[action] + said, card)
