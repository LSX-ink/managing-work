"""Room measurements book and floor-plan planner.

Rooms are saved in metres in diy-rooms.json (length runs left to right, width top to bottom, north is the top of the
plan). Doors, windows and furniture are added by wall and position, and the plan pops up drawn to scale
(pop-up kind "diy-plan", frontend/popup-diy.js). The measurements book is a table of every room with its floor,
wall and ceiling figures. Removing anything needs confirmed true.
"""

import homestore as hs
import screen
from config import Settings
from diy_store import MAX_ITEMS, MAX_ROOMS, WALLS, metres, room_key, rooms, save_rooms, sq, table, wall_area

screen.EXTRA_KINDS.add("diy-plan")
OPENINGS = {"door": ("doors", 0.83), "window": ("windows", 1.2)}
ACTIONS = ("save_room", "add_opening", "add_furniture", "show_plan", "measurements_book", "room_details", "remove")


def _dims(room: dict) -> str:
    return f"{room['length']:g} x {room['width']:g} m, {room['height']:g} m high"


def save_room(settings: Settings, name, length, width, height, unit, notes) -> str:
    found = rooms(settings)
    label = hs.need(name, "room", 40)
    old = hs.find(found, label)
    if old is None and len(found) >= MAX_ROOMS:
        raise ValueError("That's as many rooms as I can keep; remove one first.")
    room = found.get(old or label, {"doors": [], "windows": [], "items": []})
    for key, value, what in (("length", length, "length"), ("width", width, "width"), ("height", height, "ceiling height")):
        if value is not None:
            room[key] = metres(value, what, unit, low=0.1, high=100)
        elif key not in room:
            if key != "height":
                raise ValueError(f"How long is the {key} of the room?")
            room[key] = 2.4
    if hs.clean(notes):
        room["notes"] = hs.clean(notes, 200)
    found[old or label] = room
    save_rooms(settings, found)
    return f"Saved {old or label}: {_dims(room)}, floor {room['length'] * room['width']:.1f} square metres."


def _wall_len(room: dict, wall: str) -> float:
    return room["length"] if wall in ("north", "south") else room["width"]


def add_opening(settings: Settings, name, kind, wall, offset, size, unit) -> str:
    found = rooms(settings)
    k = room_key(found, name)
    room = found[k]
    kind = hs.clean(kind).lower()
    if kind not in OPENINGS:
        raise ValueError("Is it a door or a window?")
    wall = hs.clean(wall).lower()
    if wall not in WALLS:
        raise ValueError("Which wall: north, east, south or west? North is the top of the plan.")
    key, default = OPENINGS[kind]
    width = metres(size, "width", unit, high=10) if size is not None else default
    room_len = _wall_len(room, wall)
    if width > room_len:
        raise ValueError(f"That's wider than the {wall} wall, which is {room_len:g} m.")
    start = metres(offset, "position", unit, low=0, high=100) if offset is not None else (room_len - width) / 2
    start = max(0.0, min(start, room_len - width))
    room.setdefault(key, []).append({"wall": wall, "offset": round(start, 3), "width": round(width, 3)})
    save_rooms(settings, found)
    return f"Added a {kind} {width:g} m wide on the {wall} wall of {k}."


def _place(room: dict, w: float, d: float, position: str, x, y, unit) -> tuple[float, float]:
    if w > room["length"] or d > room["width"]:
        raise ValueError(f"That's bigger than the room, which is {room['length']:g} x {room['width']:g} m.")
    if x is not None and y is not None:
        px, py = metres(x, "x", unit, low=0, high=100), metres(y, "y", unit, low=0, high=100)
    else:
        text = hs.clean(position).lower()
        px = 0 if "west" in text or "left" in text else room["length"] - w if "east" in text or "right" in text else (room["length"] - w) / 2
        py = 0 if "north" in text or "top" in text else room["width"] - d if "south" in text or "bottom" in text else (room["width"] - d) / 2
    return round(max(0, min(px, room["length"] - w)), 3), round(max(0, min(py, room["width"] - d)), 3)


def add_furniture(settings: Settings, name, item, w, d, position, x, y, unit) -> screen.Shown:
    found = rooms(settings)
    k = room_key(found, name)
    room = found[k]
    label = hs.need(item, "item of furniture", 40)
    if len(room.setdefault("items", [])) >= MAX_ITEMS:
        raise ValueError("That room's plan is full.")
    width, depth = metres(w, "width", unit, high=20), metres(d if d is not None else w, "depth", unit, high=20)
    px, py = _place(room, width, depth, position, x, y, unit)
    room["items"] = [i for i in room["items"] if i["name"].lower() != label.lower()] + [
        {"name": label, "w": width, "d": depth, "x": px, "y": py}]
    save_rooms(settings, found)
    return _plan(k, room, f"Put the {label} in {k}.")


def _plan(k: str, room: dict, text: str) -> screen.Shown:
    data = {"name": k, "length": room["length"], "width": room["width"], "height": room["height"],
            "doors": room.get("doors", []), "windows": room.get("windows", []), "items": room.get("items", [])}
    buttons = [{"label": "Measurements", "say": "Show my room measurements book."},
               {"label": "Details", "say": f"Show the details of the {k}."}]
    return screen.Shown(text, screen.card("diy-plan", f"Floor plan: {k}", f"diy-plan-{k.lower()}", data=data, buttons=buttons))


def show_plan(settings: Settings, name, length, width, unit) -> screen.Shown:
    if hs.clean(name):
        found = rooms(settings)
        k = room_key(found, name)
        return _plan(k, found[k], f"Here's the plan of {k}: {_dims(found[k])}.")
    if length is None or width is None:
        raise ValueError("Which room, or how long and wide is it?")
    room = {"length": metres(length, "length", unit, high=100), "width": metres(width, "width", unit, high=100), "height": 2.4}
    return _plan("Sketch", room, f"A plan of a {room['length']:g} by {room['width']:g} metre room.")


def _row(k: str, room: dict) -> list:
    floor = room["length"] * room["width"]
    return [k, f"{room['length']:g} x {room['width']:g} x {room['height']:g}", sq(floor),
            f"{2 * (room['length'] + room['width']):.1f} m", sq(wall_area(room)),
            f"{floor * room['height']:.1f} m³"]


def measurements_book(settings: Settings) -> screen.Shown | str:
    found = rooms(settings)
    if not found:
        return "The measurements book is empty. Say a room's name and size to add it."
    rows = [_row(k, r) for k, r in sorted(found.items())]
    card = table("Room measurements", ["Room", "L x W x H (m)", "Floor", "Round", "Walls", "Volume"], rows,
                 "diy-rooms", buttons=[{"label": "Add a room", "say": "Add a room to my measurements book."}])
    return screen.Shown(f"You have {hs.plural(len(found), 'room')} in the measurements book.", card)


def room_details(settings: Settings, name) -> screen.Shown:
    found = rooms(settings)
    k = room_key(found, name)
    r = found[k]
    floor = r["length"] * r["width"]
    rows = [["Size", _dims(r)], ["Floor area", sq(floor)], ["Distance round the walls", f"{2 * (r['length'] + r['width']):.1f} m"],
            ["Wall area (less doors and windows)", sq(wall_area(r))], ["Ceiling area", sq(floor)],
            ["Volume", f"{floor * r['height']:.1f} m³"], ["Doors", str(len(r.get("doors", [])))],
            ["Windows", str(len(r.get("windows", [])))]]
    rows += [[i["name"], f"{i['w']:g} x {i['d']:g} m"] for i in r.get("items", [])]
    if r.get("notes"):
        rows.append(["Notes", r["notes"]])
    card = table(k, ["What", "Measure"], rows, f"diy-room-{k.lower()}",
                 buttons=[{"label": "Show plan", "say": f"Show the floor plan of the {k}."},
                          {"label": "Paint needed", "say": f"How much paint for the {k}?"}])
    return screen.Shown(f"{k} is {_dims(r)}. Floor {floor:.1f} square metres, walls {wall_area(r):.1f}.", card)


def remove(settings: Settings, name, item, confirmed) -> str:
    found = rooms(settings)
    k = room_key(found, name)
    if hs.clean(item):
        items = found[k].get("items", [])
        gone = hs.find([i["name"] for i in items], item)
        if gone is None:
            raise ValueError(f"There's no {hs.clean(item)} in {k}.")
        if not confirmed:
            return f"Ask the user to confirm removing the {gone} from {k}, then call again with confirmed true."
        found[k]["items"] = [i for i in items if i["name"] != gone]
        save_rooms(settings, found)
        return f"Removed the {gone} from {k}."
    if not confirmed:
        return f"Ask the user to confirm removing {k} from the measurements book, then call again with confirmed true."
    del found[k]
    save_rooms(settings, found)
    return f"Removed {k}."


def tool_definitions() -> list[dict]:
    text, num = {"type": "string"}, {"type": "number"}
    return [{
        "name": "diy_room",
        "description": "Room measurements book and floor planner (metres). action: 'save_room' name, length, width, "
                       "height (unit m, cm, mm, ft, in); 'add_opening' a door or window (kind, wall north/east/south/west, "
                       "offset from the wall's start, size); 'add_furniture' item with width and depth, position like "
                       "'north west' or x and y; 'show_plan' draws the floor plan (saved room, or length and width); "
                       "'measurements_book' table of all rooms with floor, wall and volume; 'room_details'; 'remove' a "
                       "room or a furniture item (set confirmed true only after the user confirms).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "name": {**text, "description": "Room name."},
                "length": num, "width": num, "height": num,
                "unit": {"type": "string", "enum": ["m", "cm", "mm", "ft", "in"]},
                "notes": text,
                "kind": {"type": "string", "enum": ["door", "window"]},
                "wall": {"type": "string", "enum": list(WALLS)},
                "offset": num, "size": {**num, "description": "Width of the door or window."},
                "item": {**text, "description": "Furniture name."},
                "depth": num, "position": text, "x": num, "y": num,
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"diy_room"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    actions = {
        "save_room": lambda: save_room(settings, a("name"), a("length"), a("width"), a("height"), a("unit"), a("notes")),
        "add_opening": lambda: add_opening(settings, a("name"), a("kind"), a("wall"), a("offset"), a("size"), a("unit")),
        "add_furniture": lambda: add_furniture(settings, a("name"), a("item"), a("width"), a("depth"), a("position"),
                                               a("x"), a("y"), a("unit")),
        "show_plan": lambda: show_plan(settings, a("name"), a("length"), a("width"), a("unit")),
        "measurements_book": lambda: measurements_book(settings),
        "room_details": lambda: room_details(settings, a("name")),
        "remove": lambda: remove(settings, a("name"), a("item"), a("confirmed")),
    }
    if a("action") not in actions:
        raise ValueError(f"I can't do {a('action')} with rooms.")
    return actions[a("action")]()
