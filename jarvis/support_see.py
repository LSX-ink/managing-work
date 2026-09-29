"""Everyday support, part 4: seeing things more easily. A magnifier pop-up for a picture in the memory folders (zoom
and pan), plain colour names for a photo (for colour-blind users) and the shopping list in large print.

Nothing is uploaded; pictures are read on this PC. New pop-up kind: "support-magnify", drawn by popup-support.js.
"""

import colorsys
from urllib.parse import quote

import artstudio_colours as colours
import artstudio_common as ac
import memory
import screen
import shopping
from config import Settings

screen.EXTRA_KINDS.add("support-magnify")
ACTIONS = ["magnifier", "colours", "big_shopping"]


def colour_word(hex_code: str) -> str:
    """A plain everyday name such as 'dark blue', 'light green', 'grey' or 'black'."""
    r, g, b = (c / 255 for c in colours.to_rgb(hex_code))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    if light < 0.12:
        return "black"
    if light > 0.9:
        return "white"
    if sat < 0.12:
        return "dark grey" if light < 0.4 else "light grey" if light > 0.65 else "grey"
    degrees = hue * 360
    for limit, name in ((15, "red"), (40, "orange"), (65, "yellow"), (160, "green"), (200, "turquoise"),
                        (255, "blue"), (290, "purple"), (335, "pink"), (361, "red")):
        if degrees < limit:
            break
    if name == "orange" and light < 0.4:
        name = "brown"
    if name == "red" and light > 0.75:
        name = "pink"
    return ("dark " if light < 0.3 else "light " if light > 0.7 else "") + name


def magnifier(settings: Settings, args: dict) -> screen.Shown:
    path = ac.picture(settings, args.get("folder") or "", args.get("filename") or "")
    rel = path.resolve().relative_to(memory.root(settings).resolve()).as_posix()
    c = screen.card("support-magnify", f"Magnifier: {path.name}", f"support-magnify-{rel}",
                    data={"src": f"/screen/file?path={quote(rel)}", "name": path.name})
    return screen.Shown(f"{path.name} is on the magnifier. Use the plus and minus buttons, and drag to move around.", c)


def colours_of(settings: Settings, args: dict) -> screen.Shown:
    path, im = ac.load(settings, args.get("folder") or "", args.get("filename") or "")
    merged: dict[str, list] = {}
    for hex_code, share in colours.picture_colours(im, 8):
        word = colour_word(hex_code)
        merged.setdefault(word, [0.0, hex_code])[0] += share
    found = sorted(merged.items(), key=lambda kv: -kv[1][0])
    rows = [[word, f"{round(share)}%", hex_code] for word, (share, hex_code) in found if round(share) >= 1]
    c = screen.card("table", f"Colours in {path.name}", f"support-colours-{path.name}",
                    columns=["Colour", "How much", "Code"], rows=rows)
    lead = [w for w, _ in found[:3]]
    return screen.Shown(f"{path.name} is mostly {lead[0]}" + (f", then {' and '.join(lead[1:])}." if lead[1:] else "."), c)


def big_shopping(settings: Settings) -> screen.Shown | str:
    found = shopping.items(settings)
    if not found:
        return "Your shopping list is empty."
    c = screen.card("support-big", "Shopping list", "support-shopping",
                    data={"lines": [{"label": str(i + 1), "value": item} for i, item in enumerate(found)]})
    return screen.Shown(f"Your shopping list is on the screen in large print: {len(found)} items.", c)


def tool_definitions() -> list[dict]:
    return [{
        "name": "support_see",
        "description": "Helps people with poor eyesight. action: magnifier = show a picture from the memory folders "
                       "in a zoom-and-pan magnifier (folder, filename); colours = name the main colours of a photo "
                       "in plain words such as dark blue, for colour-blind users (folder, filename); big_shopping = "
                       "the shopping list in very large print.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "folder": {"type": "string", "description": "Memory folder, e.g. Personal."},
                "filename": {"type": "string", "description": "The picture's name, or part of it."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"support_see"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "magnifier":
        return magnifier(settings, args)
    if action == "colours":
        return colours_of(settings, args)
    if action == "big_shopping":
        return big_shopping(settings)
    raise ValueError("I can't do that one.")
