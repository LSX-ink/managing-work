"""Accessibility: switch the Alfred screen's big text, high contrast, reduced motion, captions, dyslexia-friendly
font, speech speed and colour-blind colours by voice, or open the accessibility settings window.

The settings live in the browser (frontend/access.js saves them per device in localStorage), so this module only
builds a small "access-set" card that the page applies when it arrives and answers with the current settings.
"""

import screen
from config import Settings

KIND = "access-set"
screen.EXTRA_KINDS.add(KIND)

NAMES = {"accessibility_settings"}
TOGGLES = ("high_contrast", "reduce_motion", "captions", "dyslexia_font", "colour_blind")
ACTIONS = ("big_text", *TOGGLES, "speech_speed", "show_settings", "show_shortcuts", "reset")
SWITCH = {"on": "on", "off": "off", "toggle": "toggle", "yes": "on", "no": "off", "true": "on", "false": "off"}
SIZES = {"normal": "normal", "large": "large", "big": "large", "extra_large": "xl", "extra large": "xl", "xl": "xl",
         "huge": "xl", "bigger": "bigger", "smaller": "smaller", "reset": "normal"}
SPEEDS = {"slower": "slower", "slow": "slower", "faster": "faster", "fast": "faster", "normal": "normal"}
LABELS = {"high_contrast": "High contrast", "reduce_motion": "Reduced motion", "captions": "Captions",
          "dyslexia_font": "The dyslexia-friendly font", "colour_blind": "Colour-blind safe colours"}


def tool_definitions() -> list[dict]:
    return [{
        "name": "accessibility_settings",
        "description": "Make the Alfred screen easier to use: bigger or smaller text, high contrast, reduce motion or "
                       "animation, captions (subtitles of what Alfred says), dyslexia-friendly font, colour-blind "
                       "safe colours, and Alfred speaking slower or faster. Also opens the accessibility settings "
                       "window or the keyboard shortcuts list. Actions: big_text (value normal, large, "
                       "extra_large, bigger or smaller); high_contrast, reduce_motion, captions, dyslexia_font, "
                       "colour_blind (value on, off or toggle, default on); speech_speed (value slower, faster, "
                       "normal, or a multiplier such as 0.8 or 1.3); show_settings; show_shortcuts; reset (puts "
                       "every setting back). Settings are saved on this device only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "value": {"type": "string", "description": "See the action; leave out for show_settings and reset."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def _switch(action: str, value: str) -> tuple[str, str]:
    mode = SWITCH.get(value or "on")
    if not mode:
        raise ValueError("Say on, off or toggle.")
    label = LABELS[action]
    if mode == "toggle":
        return mode, f"{label} switched."
    return mode, f"{label} {mode}."


def _size(value: str) -> tuple[str, str]:
    size = SIZES.get(value or "bigger")
    if not size:
        raise ValueError("Pick normal, large, extra large, bigger or smaller.")
    words = {"normal": "Text is back to normal size.", "large": "Text is now large.",
             "xl": "Text is now extra large.", "bigger": "Text made bigger.", "smaller": "Text made smaller."}
    return size, words[size]


def _speed(value: str) -> tuple[str, str]:
    if value in SPEEDS:
        speed = SPEEDS[value]
        return speed, {"slower": "I'll speak more slowly.", "faster": "I'll speak faster.",
                       "normal": "I'll speak at my usual speed."}[speed]
    try:
        rate = float(value)
    except (TypeError, ValueError):
        raise ValueError("Say slower, faster, normal or a number like 0.8.") from None
    if not 0.5 <= rate <= 2:
        raise ValueError("Speech speed has to be between 0.5 and 2 times normal.")
    return f"{rate:g}", f"I'll speak at {rate:g} times my usual speed."


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action") or "show_settings"
    value = str(args.get("value") or "").strip().lower()
    if action not in ACTIONS:
        raise ValueError("Pick one of: " + ", ".join(ACTIONS) + ".")
    if action == "big_text":
        value, text = _size(value)
    elif action in TOGGLES:
        value, text = _switch(action, value)
    elif action == "speech_speed":
        value, text = _speed(value or "faster")
    else:
        value = ""
        text = {"show_settings": "Here are the accessibility settings.",
                "show_shortcuts": "Here are the keyboard shortcuts.",
                "reset": "All accessibility settings are back to normal."}[action]
    card = screen.card(KIND, "Accessibility", "access-settings", data={"action": action, "value": value})
    return screen.Shown(text, card)
