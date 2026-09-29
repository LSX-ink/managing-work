"""DIY how-to guides and reference: step-by-step checklists with safety notes, safety reminders, drill bits,
screw sizes, wall fixings, paint finishes and wood stains.

A how-to pops up as a checklist you tick as you go (pop-up kind "diy-guide", frontend/popup-diy.js); the ticks are
just for the page. Everything is built in (diy_data.py); nothing is saved and nothing goes online.
"""

import homestore as hs
import screen
from config import Settings
from diy_data import DRILL_BITS, FINISHES, FIXINGS, GUIDES, SAFETY, SCREWS, STAINS
from diy_store import table

screen.EXTRA_KINDS.add("diy-guide")
ACTIONS = ("how_to", "safety", "drill_bits", "screw_sizes", "wall_fixings", "paint_finish", "wood_stain")


def _pick(options, wanted, what: str) -> str | None:
    if not hs.clean(wanted):
        return None
    words = hs.clean(wanted).lower().replace("-", " ")
    keys = list(options)
    found = hs.find(keys, words)
    if found is None:
        found = next((k for k in keys if all(w in k for w in words.split() if len(w) > 2)), None)
    if found is None:
        raise ValueError(f"I haven't got a {what} for {hs.clean(wanted)}. Try: {', '.join(keys)}.")
    return found


def how_to(name) -> screen.Shown:
    key = _pick(GUIDES, name, "guide")
    if key is None:
        rows = [[k.capitalize(), f"{v[0]} min", v[1]] for k, v in GUIDES.items()]
        card = table("DIY how-to guides", ["Guide", "Time", "Level"], rows, "diy-howto-list")
        return screen.Shown("I have guides for: " + ", ".join(GUIDES) + ".", card)
    minutes, level, tools, safety, steps, pro = GUIDES[key]
    data = {"title": key.capitalize(), "minutes": minutes, "level": level, "tools": tools, "safety": safety,
            "steps": steps, "pro": pro}
    card = screen.card("diy-guide", key.capitalize(), f"diy-guide-{key.replace(' ', '-')}", data=data,
                       buttons=[{"label": "Safety reminders", "say": "What are the DIY safety reminders before drilling?"}])
    return screen.Shown(f"Here's how to {key}: {len(steps)} steps, about {minutes} minutes. "
                        f"Safety first: {safety[0]}", card)


def safety(topic) -> screen.Shown:
    key = _pick(SAFETY, topic, "safety topic")
    if key is None:
        rows = [[k.capitalize(), v[0]] for k, v in SAFETY.items()]
        card = table("DIY safety reminders", ["Topic", "About"], rows, "diy-safety-list")
        return screen.Shown("Safety topics: " + ", ".join(SAFETY) + ".", card)
    title, points = SAFETY[key]
    items = [{"label": p} for p in points]
    card = screen.card("list", title, f"diy-safety-{key.replace(' ', '-')}", items=items,
                       buttons=[{"label": "All topics", "say": "What DIY safety reminders have you got?"}])
    return screen.Shown(f"{title}: {points[0]} {len(points) - 1} more on screen.", card)


def drill_bits(material) -> screen.Shown:
    wanted = hs.clean(material).lower()
    rows = [list(r) for r in DRILL_BITS if not wanted or wanted in r[0].lower() or r[0].lower() in wanted]
    if not rows:
        raise ValueError(f"I haven't got drilling advice for {wanted}. Try wood, metal, brick, concrete, tile, glass or plasterboard.")
    card = table("Drill bits by material", ["Material", "Bit", "Speed", "Tips"], rows, "diy-drill")
    return screen.Shown(f"For {rows[0][0].lower()}: {rows[0][1]}, {rows[0][2].lower()} speed. {rows[0][3]}"
                        if len(rows) == 1 else "Here's which drill bit for each material.", card)


def screw_sizes(gauge) -> screen.Shown:
    wanted = hs.clean(gauge).lower().replace("no.", "").replace("no", "").strip()
    rows = [[g, f"{d:g} mm", f"{c:g} mm", f"{s:g} mm", f"{h:g} mm"] for g, d, c, s, h in SCREWS
            if not wanted or wanted == g.split()[-1] or wanted.rstrip("mm ") == f"{d:g}"]
    if not rows:
        raise ValueError("Which screw gauge, from No. 4 to No. 14?")
    card = table("Screw and drill bit sizes", ["Gauge", "Diameter", "Clearance hole", "Pilot (softwood)", "Pilot (hardwood)"],
                 rows, "diy-screws")
    first = rows[0]
    text = (f"A {first[0]} screw is {first[1]} across: drill {first[2]} clearance, and {first[3]} pilot in softwood."
            if len(rows) == 1 else "Here are the drill sizes for each screw gauge.")
    return screen.Shown(text + " Sizes are a guide.", card)


def wall_fixings(wall) -> screen.Shown:
    wanted = hs.clean(wall).lower()
    rows = [list(r) for r in FIXINGS if not wanted or any(w in r[0].lower() for w in wanted.replace("-", " ").split() if len(w) > 2)]
    rows = rows or [list(r) for r in FIXINGS]
    card = table("Which wall fixing", ["Wall", "Fixing", "Drill", "Notes"], rows, "diy-fixings")
    text = f"For {rows[0][0].lower()}: {rows[0][1]}." if len(rows) == 1 else "Here's the right fixing for each type of wall."
    return screen.Shown(text + " Check the load rating on the pack.", card)


def _guide_table(rows, wanted, title: str, columns: list[str], card_id: str, empty: str) -> screen.Shown:
    words = [w for w in hs.clean(wanted).lower().replace("-", " ").split() if len(w) > 2]
    match = [list(r) for r in rows if not words or any(w in " ".join(r).lower() for w in words)]
    if not match:
        raise ValueError(empty)
    card = table(title, columns, match, card_id)
    text = f"{match[0][0]}: {match[0][2 if len(match[0]) > 3 else 1]}." if len(match) == 1 else f"Here's the {title.lower()}."
    return screen.Shown(text, card)


def paint_finish(finish) -> screen.Shown:
    return _guide_table(FINISHES, finish, "Paint finishes", ["Finish", "Sheen", "Best for", "Notes"], "diy-finishes",
                        "Try matt, silk, eggshell, satin, gloss or masonry.")


def wood_stain(kind) -> screen.Shown:
    return _guide_table(STAINS, kind, "Wood stains and finishes", ["Type", "Look", "Best for", "Notes"], "diy-stains",
                        "Try stain, oil, varnish, decking or wax.")


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "diy_guide",
        "description": "DIY how-to guides and reference. action: 'how_to' a step-by-step tick-list with safety notes "
                       "(bleed a radiator, change a fuse, unblock a sink, fix a dripping tap, hang a picture level, "
                       "reset a tripped RCD, stopcock, patch plasterboard, reseal a bath, paint a room, hang a shelf, "
                       "unblock a toilet; no topic lists them); 'safety' reminders (before you drill, electrics, gas, "
                       "water, ladders, asbestos, lead paint, dust, power tools, lifting; use before drilling walls "
                       "for studs and pipes); 'drill_bits' by material; 'screw_sizes' clearance and pilot holes by "
                       "gauge; 'wall_fixings' plugs and toggles by wall type; 'paint_finish' matt, silk, gloss guide; "
                       "'wood_stain' stain, oil and varnish guide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "topic": {**text, "description": "Guide, safety topic, material, screw gauge, wall type, finish or stain."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"diy_guide"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    topic = args.get("topic")
    actions = {"how_to": how_to, "safety": safety, "drill_bits": drill_bits, "screw_sizes": screw_sizes,
               "wall_fixings": wall_fixings, "paint_finish": paint_finish, "wood_stain": wood_stain}
    if args.get("action") not in actions:
        raise ValueError(f"I can't do {args.get('action')} with DIY guides.")
    return actions[args["action"]](topic)
