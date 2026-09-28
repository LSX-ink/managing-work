"""Alfred's speaking voice: pick a more natural browser voice, and change how fast or deep he speaks.

The voices live in the browser (Windows, Edge and Chrome each have their own), so this module only builds a
card; frontend/voice.js lists the voices, plays samples and saves the choice in that browser.
With ELEVENLABS_API_KEY set, Alfred speaks with the ElevenLabs voice instead and the browser voice is unused.
"""

import screen
from config import Settings

KIND = "voice-picker"
screen.EXTRA_KINDS.add(KIND)

NAMES = {"change_voice"}
ACTIONS = ("choose", "soldier", "faster", "slower", "deeper", "higher", "reset")
SPOKEN = {
    "choose": "Here are the voices I can use. Press Try to hear one and Use to pick it.",
    "faster": "I'll speak a little faster.",
    "slower": "I'll speak a little slower.",
    "deeper": "I'll speak a little deeper.",
    "higher": "I'll speak a little higher.",
    "soldier": "Understood. Deep, steady and British, as ordered.",
    "reset": "My voice is back to its usual calm speed and pitch.",
}


def tool_definitions() -> list[dict]:
    return [{
        "name": "change_voice",
        "description": "Change Alfred's own speaking voice when the user says he sounds robotic or asks for a "
                       "different voice, accent, speed or pitch. 'choose' pops up the list of voices on this "
                       "computer to try and pick (the most natural ones are marked); 'soldier' goes back to his default deep, "
                       "serious British man's voice; 'faster', 'slower', "
                       "'deeper', 'higher' adjust the current voice; 'reset' puts speed and pitch back.",
        "input_schema": {
            "type": "object",
            "properties": {"action": {"type": "string", "enum": list(ACTIONS)}},
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action") or "choose"
    if action not in ACTIONS:
        raise ValueError("Pick one of: " + ", ".join(ACTIONS) + ".")
    text = SPOKEN[action]
    if settings.elevenlabs_api_key:
        text += (" I'm using the ElevenLabs voice at the moment, so to change how I sound, change "
                 "ELEVENLABS_VOICE_ID in the .env file; the browser voices only apply without ElevenLabs.")
    card = screen.card(KIND, "Alfred's voice", "voice-picker",
                       data={"action": action, "lang": settings.speech_lang,
                             "server_voice": bool(settings.elevenlabs_api_key)})
    return screen.Shown(text, card)
