"""Leftovers in the fridge with eat-by dates: 2 days by default, 3 for soups, stews and curries, 1 for rice.

Kept in cooking-leftovers.json in the memory folder. The freezer has its own list (household_stuff).
"""

from datetime import timedelta

import cooking_store as cs
import homestore as hs
import screen
from config import Settings

ACTIONS = ["add", "list", "eaten", "clear_old"]
MAX_LEFTOVERS = 100
RICE = ("rice", "risotto", "paella", "biryani", "pilau", "fried rice")
LONGER = ("soup", "stew", "curry", "chilli", "casserole", "bolognese", "dal", "tagine", "ragu")


def rule_days(what: str) -> int:
    text = what.lower()
    if any(w in text for w in RICE):
        return 1
    return 3 if any(w in text for w in LONGER) else 2


def _load(settings: Settings) -> list[dict]:
    return [i for i in hs.load(settings, cs.LEFTOVERS, []) if isinstance(i, dict) and i.get("what")]


def add(settings: Settings, what, cooked_on=None, days=None) -> str:
    what = hs.need(what, "leftovers", 60)
    cooked = hs.parse_day(cooked_on)
    keep = int(hs.number(days, "number of days", 1, 3)) if days is not None else rule_days(what)
    eat_by = cooked + timedelta(days=keep)
    found = _load(settings)
    if len(found) >= MAX_LEFTOVERS:
        raise ValueError("The leftovers list is full; clear some old ones first.")
    found.append({"what": what, "cooked": cooked.isoformat(), "eat_by": eat_by.isoformat()})
    hs.save(settings, cs.LEFTOVERS, found)
    tip = " Rice is best eaten within a day; cool it quickly." if keep == 1 else ""
    return f"Logged {what}; eat by {hs.spoken(eat_by)}.{tip}"


def _state(eat_by: str) -> tuple[str, int]:
    left = (hs.parse_day(eat_by) - hs.today()).days
    if left < 0:
        return "past its date, bin it", left
    return ("eat today", left) if left == 0 else ("eat by tomorrow", left) if left == 1 else (f"{left} days left", left)


def show(settings: Settings) -> screen.Shown:
    found = sorted(_load(settings), key=lambda i: i.get("eat_by", ""))
    items = []
    for i in found:
        state, _ = _state(i["eat_by"])
        items.append({"label": f"{i['what']}: {state} (cooked {i['cooked']})",
                      "say": f"I've eaten the leftover {i['what']}."})
    old = [i["what"] for i in found if _state(i["eat_by"])[1] < 0]
    today = [i["what"] for i in found if _state(i["eat_by"])[1] == 0]
    buttons = [{"label": "Clear old ones", "say": "Clear the leftovers that are past their date."}] if old else []
    card = screen.card("list", "Leftovers", "cooking-leftovers", items=items, checks=True, buttons=buttons,
                       text="Tick one when it's eaten. Reheat until steaming hot, and only once.")
    if not found:
        return screen.Shown("No leftovers logged.", card)
    warn = [f"throw away {', '.join(old)}" if old else "", f"eat {', '.join(today)} today" if today else ""]
    warn = " and ".join(w for w in warn if w)
    return screen.Shown(f"{hs.plural(len(found), 'leftover')} in the fridge" + (f"; {warn}." if warn else "."), card)


def eaten(settings: Settings, what) -> str:
    word = hs.need(what, "leftovers").lower()
    found = _load(settings)
    match = next((i for i in found if i["what"].lower() == word), None) or \
        next((i for i in found if word in i["what"].lower()), None)
    if not match:
        return f"There are no leftovers called {hs.clean(what)}."
    found.remove(match)
    hs.save(settings, cs.LEFTOVERS, found)
    return f"Crossed off the {match['what']}. {hs.plural(len(found), 'leftover')} left."


def clear_old(settings: Settings, confirmed: bool) -> str:
    found = _load(settings)
    old = [i["what"] for i in found if _state(i["eat_by"])[1] < 0]
    if not old:
        return "Nothing is past its date."
    if not confirmed:
        return f"Ask the user to confirm clearing {', '.join(old)}, then call again with confirmed true."
    hs.save(settings, cs.LEFTOVERS, [i for i in found if _state(i["eat_by"])[1] >= 0])
    return f"Cleared {', '.join(old)}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "cooking_leftovers",
        "description": "Leftovers log with eat-by dates (2 days, 3 for soups/stews/curries, 1 for rice) and warnings. "
                       "add (what, cooked_on YYYY-MM-DD/today/yesterday, optional days 1-3), list pops up the "
                       "leftovers with what to eat or bin, eaten (what) crosses one off, clear_old removes those past "
                       "their date: set confirmed true only after the user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "what": {"type": "string"},
                "cooked_on": {"type": "string"},
                "days": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"cooking_leftovers"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "add":
        return add(settings, args.get("what"), args.get("cooked_on"), args.get("days"))
    if action == "eaten":
        return eaten(settings, args.get("what"))
    if action == "clear_old":
        return clear_old(settings, bool(args.get("confirmed")))
    return show(settings)
