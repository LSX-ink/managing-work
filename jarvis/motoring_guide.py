"""Motoring reference, all built in and offline: UK speed limits, Highway Code stopping distances, what dashboard
warning lights mean, congestion and low emission zone facts, and the breakdown, accident, winter kit, road trip and
used-car checklists.
"""

import motoring_data as data
import screen
from config import Settings

screen.EXTRA_KINDS.add("motoring-lights")

ACTIONS = ["speed_limits", "stopping_distances", "warning_lights", "zones", "checklist"]
LISTS = list(data.CHECKLISTS)


def tool_definitions() -> list[dict]:
    return [{
        "name": "motoring_guide",
        "description": "UK driving reference. speed_limits (national speed limit table by vehicle), "
                       "stopping_distances (Highway Code thinking, braking and total distance at each speed), "
                       "warning_lights (what a dashboard warning light means, red or amber: engine, oil, battery, "
                       "tyre, ABS, DPF...), zones (London ULEZ, congestion charge, clean air zones), checklist "
                       "(breakdown, accident, winter car kit, road trip packing, used car buying).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "speed": {"type": "number", "description": "stopping_distances: speed in mph to speak about."},
                "light": {"type": "string", "description": "warning_lights: which light, e.g. 'oil' or 'engine'."},
                "list": {"type": "string", "enum": LISTS},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"motoring_guide"}


def run_tool(name: str, args: dict, settings: Settings):
    action = args.get("action")
    if action not in ACTIONS:
        raise ValueError(f"Unknown action {action}.")
    return globals()[action](args)


def speed_limits(args: dict) -> screen.Shown:
    card = screen.card("table", "UK speed limits (mph)", "motoring-limits", columns=data.SPEED_COLUMNS,
                       rows=data.SPEED_LIMITS, text=data.SPEED_NOTE)
    return screen.Shown("For a car it's 30 in built-up areas, 60 on single carriageways and 70 on dual carriageways "
                        "and motorways. The full table is on screen.", card)


def stopping_distances(args: dict) -> screen.Shown:
    rows = [[str(s), str(t), str(b), str(total), f"{total / 4:.0f}"] for s, t, b, total in data.STOPPING]
    said = "Stopping distances are on screen."
    if args.get("speed"):
        near = min(data.STOPPING, key=lambda r: abs(r[0] - float(args["speed"])))
        said = (f"At {near[0]} mph you need about {near[3]} metres to stop: {near[1]} thinking and {near[2]} braking, "
                f"about {near[3] // 4} car lengths.")
    card = screen.card("table", "Stopping distances", "motoring-stopping",
                       columns=["Speed mph", "Thinking m", "Braking m", "Total m", "Car lengths"], rows=rows,
                       text=data.STOPPING_NOTE)
    return screen.Shown(said, card)


def warning_lights(args: dict) -> screen.Shown:
    query = str(args.get("light") or "").strip().lower()
    found = [x for x in data.LIGHTS if query and query in x[0].lower()] or list(data.LIGHTS)
    lights = [{"name": n, "colour": c, "meaning": m, "action": a} for n, c, m, a in found]
    if query and len(found) < len(data.LIGHTS):
        n, c, m, a = found[0]
        said = f"The {n.lower()} light is {c}: {m} {a}"
    else:
        said = "The common warning lights are on screen. Red means stop safely, amber means get it checked soon."
    card = screen.card("motoring-lights", "Dashboard warning lights", "motoring-lights", text=data.LIGHT_NOTE,
                       data={"lights": lights})
    return screen.Shown(said, card)


def zones(args: dict) -> screen.Shown:
    card = screen.card("table", "Congestion and low emission zones", "motoring-zones", columns=["Zone", "Facts"],
                       rows=data.ZONES)
    return screen.Shown("London's ULEZ covers every borough and the Congestion Charge covers the centre. "
                        "The details are on screen; check tfl.gov.uk for current prices.", card)


def checklist(args: dict) -> screen.Shown:
    which = args.get("list")
    if which not in data.CHECKLISTS:
        raise ValueError(f"Which checklist? {', '.join(LISTS)}.")
    title, items = data.CHECKLISTS[which]
    card = screen.card("list", title, f"motoring-{which}", items=[{"label": i} for i in items])
    return screen.Shown(f"{title}: {len(items)} points, on screen.", card)
