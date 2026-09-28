"""Chance and passwords: coin flips, dice, random numbers, picking from a list, and strong passwords.

Everything uses the secrets module. Passwords are made fresh each time and never stored.
"""

import re
import secrets
import string

from config import Settings

SYMBOLS = "!#$%&*+-=?@^_~"


def coin() -> str:
    return f"It's {secrets.choice(['heads', 'tails'])}."


def dice(spec: str) -> str:
    match = re.fullmatch(r"\s*(\d*)\s*d\s*(\d+)\s*(?:([+-])\s*(\d+))?\s*", str(spec or "1d6").lower())
    if not match:
        raise ValueError("Say the dice like 2d6: how many dice, d, then how many sides.")
    count, sides = int(match.group(1) or 1), int(match.group(2))
    bonus = int(match.group(4) or 0) * (-1 if match.group(3) == "-" else 1)
    if not 1 <= count <= 100 or not 2 <= sides <= 1000:
        raise ValueError("I can roll 1 to 100 dice with 2 to 1000 sides.")
    rolls = [secrets.randbelow(sides) + 1 for _ in range(count)]
    total = sum(rolls) + bonus
    if count == 1 and not bonus:
        return f"You rolled {total}."
    shown = ", ".join(map(str, rolls)) + (f", {'plus' if bonus > 0 else 'minus'} {abs(bonus)}" if bonus else "")
    return f"You rolled {shown}: total {total}."


def number(low, high) -> str:
    low, high = int(low if low is not None else 1), int(high if high is not None else 100)
    if low > high:
        low, high = high, low
    if high - low > 10 ** 12:
        raise ValueError("That range is too wide.")
    return f"{low + secrets.randbelow(high - low + 1)} (between {low} and {high})."


def pick(options) -> str:
    choices = [str(o).strip() for o in (options or []) if str(o).strip()][:100]
    if len(choices) < 2:
        raise ValueError("Give me at least two things to pick from.")
    return f"I pick {secrets.choice(choices)}."


def password(length=None, symbols=None) -> str:
    length = int(length or 16)
    if not 8 <= length <= 64:
        raise ValueError("Passwords can be 8 to 64 characters long.")
    groups = [string.ascii_lowercase, string.ascii_uppercase, string.digits] + ([SYMBOLS] if symbols is not False else [])
    alphabet = "".join(groups)
    while True:
        made = "".join(secrets.choice(alphabet) for _ in range(length))
        if all(any(c in group for c in made) for group in groups):
            return (f"Password (show it on screen; don't read it aloud unless asked): {made}")


def tool_definitions() -> list[dict]:
    return [{
        "name": "chance",
        "description": "Fair random results. action 'coin' flips a coin; 'dice' rolls dice like '2d6' or 'd20+3'; "
                       "'number' picks a whole number from low to high (default 1 to 100); 'pick' chooses one of "
                       "options; 'password' makes a strong password (length 8 to 64, default 16; symbols default "
                       "true). Passwords are for the screen: do not read them aloud unless the user asks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["coin", "dice", "number", "pick", "password"]},
                "dice": {"type": "string"}, "low": {"type": "integer"}, "high": {"type": "integer"},
                "options": {"type": "array", "items": {"type": "string"}},
                "length": {"type": "integer"}, "symbols": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"chance"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action = args.get("action")
    if action == "dice":
        return dice(args.get("dice") or "1d6")
    if action == "number":
        return number(args.get("low"), args.get("high"))
    if action == "pick":
        return pick(args.get("options"))
    if action == "password":
        return password(args.get("length"), args.get("symbols"))
    return coin()
