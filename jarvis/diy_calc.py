"""DIY materials calculators (metric, UK sizes): paint, wallpaper, tiles, laminate, skirting, fencing, concrete,
decking, grout, plasterboard, gravel, turf and bricks.

Give a saved room's name (see diy_room) or the sizes in metres. Every answer pops up a small table of what to buy
with the sums behind it. Nothing is saved and nothing goes online. Coverage figures are typical; check the tin or pack.
"""

import homestore as hs
import screen
from config import Settings
from diy_store import count, metres, room_key, rooms, sq, table, up, with_extra

WHAT = ("paint", "wallpaper", "floor_tiles", "laminate", "skirting", "fence", "concrete", "decking", "grout",
        "plasterboard", "gravel", "turf", "bricks")
TINS = (10, 5, 2.5)


def _dims(a, settings: Settings) -> dict:
    """Length, width, height, doors and windows from a saved room or from the arguments."""
    unit = a("unit")
    p = {"doors": count(a("doors"), "number of doors", 50), "windows": count(a("windows"), "number of windows", 50)}
    if hs.clean(a("room")):
        found = rooms(settings)
        room = found[room_key(found, a("room"))]
        p.update(length=room["length"], width=room["width"], height=room["height"])
        p["doors"] = p["doors"] or len(room.get("doors", []))
        p["windows"] = p["windows"] or len(room.get("windows", []))
    for key in ("length", "width", "height"):
        if a(key) is not None:
            p[key] = metres(a(key), key, unit)
    return p


def _need(p: dict, *keys) -> None:
    missing = [k for k in keys if not p.get(k)]
    if missing:
        raise ValueError(f"I need the {' and '.join(missing)} (in metres), or the name of a saved room.")


def _area(p: dict, a) -> float:
    if a("area_m2") is not None:
        return hs.number(a("area_m2"), "area", 0.01, 100_000)
    _need(p, "length", "width")
    return p["length"] * p["width"]


def _walls(p: dict, a) -> float:
    if a("area_m2") is not None:
        return hs.number(a("area_m2"), "area", 0.01, 100_000)
    _need(p, "length", "width", "height")
    return 2 * (p["length"] + p["width"]) * p["height"] - 1.6 * p["doors"] - 1.2 * p["windows"]


def _waste(a, default: float) -> float:
    return a("wastage_pct") if a("wastage_pct") is not None else default


def _ceiling(p: dict, a) -> float:
    return p["length"] * p["width"] if a("include_ceiling") and p.get("length") and p.get("width") else 0


def _tins(litres: float) -> str:
    left, out = up(litres * 2) / 2, []
    for size in TINS:
        n = int(left // size)
        if n:
            out.append(f"{n} x {size:g} L")
            left -= n * size
    if left > 0:
        out.append("1 x 1 L" if left <= 1 else "1 x 2.5 L")
    return " + ".join(out)


def paint(p, a):
    area = _walls(p, a) + _ceiling(p, a)
    coats = count(a("coats") or 2, "coats", 6)
    litres = area * coats / hs.number(a("coverage_m2_per_litre") or 12, "coverage", 1, 30)
    return f"about {litres:.1f} litres of paint", [
        ["Area to paint", sq(area), "Walls less doors and windows" + (", plus ceiling" if a("include_ceiling") else "")],
        ["Coats", str(coats), "Two is usual; three over a dark colour"],
        ["Paint needed", f"{litres:.1f} L", "At about 12 m² per litre"],
        ["Tins to buy", _tins(litres), "Rounded up to half a litre"]]


def wallpaper(p, a):
    _need(p, "length", "width", "height")
    roll_w = metres(a("roll_width_m") or 0.53, "roll width")
    roll_l = metres(a("roll_length_m") or 10.05, "roll length")
    repeat = metres(a("pattern_repeat_m"), "pattern repeat", low=0) if a("pattern_repeat_m") else 0
    drop = p["height"] + 0.1
    drop = up(drop / repeat) * repeat if repeat else drop
    per_roll = int(roll_l // drop)
    if not per_roll:
        raise ValueError("The walls are taller than one roll; check the roll length.")
    round_room = 2 * (p["length"] + p["width"])
    drops = max(up(round_room / roll_w) - (p["doors"] + p["windows"]) // 2, 1)
    rolls = up(drops / per_roll)
    return f"{rolls} rolls of wallpaper", [
        ["Drops (strips)", str(drops), f"Room round {round_room:.1f} m, roll {roll_w * 100:.0f} cm wide"],
        ["Length of each drop", f"{drop:.2f} m", "Wall height plus 10 cm to trim" + (", rounded to the pattern repeat" if repeat else "")],
        ["Drops per roll", str(per_roll), f"{roll_l:.2f} m roll"],
        ["Rolls to buy", str(rolls), "One fewer drop for each pair of doors and windows"]]


def _tile_size(a) -> tuple[float, float]:
    w = hs.number(a("tile_w_mm") or 300, "tile width", 10, 3000)
    return w, hs.number(a("tile_h_mm") or w, "tile height", 10, 3000)


def floor_tiles(p, a):
    area = _area(p, a)
    tw, th = _tile_size(a)
    joint = hs.number(a("joint_mm") if a("joint_mm") is not None else 3, "joint width", 0, 20)
    waste = _waste(a, 10)
    n = up(with_extra(area / ((tw + joint) * (th + joint) / 1e6), waste))
    rows = [["Area", sq(area), ""], ["Tile", f"{tw:g} x {th:g} mm", f"{joint:g} mm joints"],
            ["Tiles to buy", str(n), f"Includes {waste:g}% for cuts and breakages"]]
    if a("pack_m2"):
        boxes = up(with_extra(area, waste) / hs.number(a("pack_m2"), "box size", 0.1, 50))
        rows.append(["Boxes", str(boxes), f"At {a('pack_m2')} m² a box"])
    rows.append(["Adhesive", f"{up(area / 4)} x 5 kg", "About 4 m² per 5 kg tub of ready-mixed adhesive"])
    return f"{n} tiles", rows


def laminate(p, a):
    area = _area(p, a)
    pack = hs.number(a("pack_m2") or 2.2, "pack size", 0.1, 50)
    waste = _waste(a, 7)
    need = with_extra(area, waste)
    packs = up(need / pack)
    return f"{packs} packs of laminate", [
        ["Floor area", sq(area), ""], ["With wastage", sq(need), f"{waste:g}% extra (10% if laid on the diagonal)"],
        ["Packs to buy", str(packs), f"At {pack:g} m² a pack"],
        ["Underlay", f"{up(area / 15)} x 15 m² rolls", "Same area as the floor"]]


def skirting(p, a):
    if a("run_m") is not None:
        run = hs.number(a("run_m"), "run", 0.1, 1000)
    else:
        _need(p, "length", "width")
        run = 2 * (p["length"] + p["width"]) - 0.8 * p["doors"]
    board = metres(a("board_length_m") or 2.4, "board length")
    need = with_extra(run, _waste(a, 10))
    n = up(need / board)
    return f"{n} lengths of skirting board", [
        ["Run of wall", f"{run:.1f} m", "Room round, less 0.8 m for each door"],
        ["With wastage", f"{need:.1f} m", "10% for mitred corners and offcuts"],
        ["Boards to buy", str(n), f"{board:g} m lengths"], ["Corners", "4", "Mitre them, or buy corner blocks"]]


def fence(p, a):
    if a("run_m") is None:
        raise ValueError("How long is the fence run, in metres?")
    run = hs.number(a("run_m"), "run", 0.5, 1000)
    panel = metres(a("panel_width_m") or 1.83, "panel width")
    n = up(run / panel)
    bags = hs.number(a("bags_per_post") or 2, "bags per post", 1, 8)
    return f"{n} fence panels and {n + 1} posts", [
        ["Fence run", f"{run:.1f} m", ""], ["Panels", str(n), f"{panel:g} m wide (standard 6 ft panels are 1.83 m)"],
        ["Posts", str(n + 1), "One more than the panels; 2.4 m posts suit a 1.8 m fence"],
        ["Gravel boards", str(n), "Optional: keeps panels off damp soil"],
        ["Postmix", f"{up((n + 1) * bags)} x 20 kg bags", f"About {bags:g} bags a post"]]


def concrete(p, a):
    area = _area(p, a)
    depth = hs.number(a("depth_mm") or 100, "depth", 10, 2000)
    vol = area * depth / 1000
    need = with_extra(vol, _waste(a, 10))
    return f"{need:.2f} cubic metres of concrete", [
        ["Volume", f"{vol:.2f} m³", f"{sq(area)} at {depth:g} mm deep"], ["With wastage", f"{need:.2f} m³", "10% spare"],
        ["Bags of postmix", f"{up(need * 100)} x 20 kg", "About 100 bags a cubic metre; fine for small jobs"],
        ["Ballast and cement", f"{need * 2.4:.1f} tonnes", "For big pads, mix it or order ready-mix"]]


def decking(p, a):
    area = _area(p, a)
    board_w = hs.number(a("board_w_mm") or 140, "board width", 50, 300)
    board_l = metres(a("board_length_m") or 2.4, "board length")
    n = up(with_extra(area / ((board_w + 5) / 1000 * board_l), _waste(a, 10)))
    span = p.get("width") or area ** 0.5
    joists = up(area / span / 0.4) + 1
    return f"{n} decking boards", [
        ["Deck area", sq(area), ""],
        ["Boards", str(n), f"{board_w:g} mm wide, {board_l:g} m long, 5 mm gaps, 10% spare"],
        ["Joists", f"{joists} x {span:.1f} m", "At 400 mm centres; 600 mm suits thick boards"],
        ["Screws", str(up(n * (span / 0.4 + 1) * 2 / 100) * 100), "Two per board at each joist"]]


def grout(p, a):
    area = _area(p, a)
    tw, th = _tile_size(a)
    joint = hs.number(a("joint_mm") or 3, "joint width", 1, 20)
    thick = hs.number(a("tile_thickness_mm") or 8, "tile thickness", 3, 30)
    kg = area * (tw + th) / (tw * th) * joint * thick * 1.6 * 1.1
    return f"about {kg:.1f} kilos of grout", [
        ["Area", sq(area), f"{tw:g} x {th:g} mm tiles"], ["Joint", f"{joint:g} mm wide, {thick:g} mm deep", ""],
        ["Grout", f"{kg:.1f} kg", "Includes 10% spare"], ["Bags", f"{up(kg / 2.5)} x 2.5 kg", "Or 5 kg bags for big rooms"]]


def plasterboard(p, a):
    area = _walls(p, a) + _ceiling(p, a)
    sheet = hs.number(a("sheet_m2") or 2.88, "sheet size", 0.5, 10)
    n = up(with_extra(area / sheet, _waste(a, 10)))
    return f"{n} sheets of plasterboard", [
        ["Area to board", sq(area), "Walls less openings" + (", plus ceiling" if a("include_ceiling") else "")],
        ["Sheets", str(n), f"{sheet:g} m² each (2400 x 1200 mm), 10% spare"],
        ["Screws", str(up(n * 30 / 100) * 100), "About 30 per sheet"],
        ["Joint tape and filler", "1 roll, 1 bag", "For taping and skimming the joints"]]


def gravel(p, a):
    area = _area(p, a)
    depth = hs.number(a("depth_mm") or 50, "depth", 10, 1000)
    tonnes = area * depth / 1000 * 1.6
    return f"about {tonnes:.1f} tonnes of gravel", [
        ["Area", sq(area), f"{depth:g} mm deep (50 mm for paths)"],
        ["Weight", f"{tonnes:.2f} tonnes", "About 1.6 tonnes a cubic metre"],
        ["Bulk bags", str(up(tonnes / 0.85)), "About 850 kg a bag"], ["Weed membrane", sq(area), "Lay it underneath"]]


def turf(p, a):
    area = _area(p, a)
    roll = hs.number(a("pack_m2") or 1, "roll size", 0.1, 20)
    n = up(with_extra(area, _waste(a, 5)) / roll)
    return f"{n} rolls of turf", [
        ["Lawn area", sq(area), ""], ["Rolls", str(n), f"{roll:g} m² each (usually 1 m²), 5% spare"],
        ["Topsoil", f"{area * 0.075:.2f} m³", "A 75 mm layer if the soil is poor"]]


def bricks(p, a):
    area = _walls(p, a)
    n = up(with_extra(area * 60, _waste(a, 5)))
    return f"{n} bricks", [
        ["Wall area", sq(area), "Length x height for a garden wall"],
        ["Bricks", str(n), "About 60 a square metre with 10 mm joints, 5% spare"],
        ["Mortar", f"{up(area * 30 / 25)} x 25 kg bags", "Roughly 30 kg per m² of wall"]]


CALCS = {"paint": paint, "wallpaper": wallpaper, "floor_tiles": floor_tiles, "laminate": laminate,
         "skirting": skirting, "fence": fence, "concrete": concrete, "decking": decking, "grout": grout,
         "plasterboard": plasterboard, "gravel": gravel, "turf": turf, "bricks": bricks}


def calculate(settings: Settings, what: str, a) -> screen.Shown:
    headline, rows = CALCS[what](_dims(a, settings), a)
    title = what.replace("_", " ").capitalize()
    card = table(f"{title} calculator", ["Item", "Amount", "Working"], rows, f"diy-calc-{what}")
    return screen.Shown(f"For {title.lower()} you need {headline}.", card)


def tool_definitions() -> list[dict]:
    num = {"type": "number"}
    return [{
        "name": "diy_calc",
        "description": "DIY materials calculator (metres, UK sizes). what: paint litres, wallpaper rolls, floor_tiles, "
                       "laminate packs, skirting board, fence panels and posts, concrete or postmix bags, decking "
                       "boards, grout, plasterboard sheets, gravel tonnes, turf rolls, bricks. Give room (a saved room) "
                       "or length, width, height (unit m, cm, mm, ft or in), or area_m2 or run_m.",
        "input_schema": {
            "type": "object",
            "properties": {
                "what": {"type": "string", "enum": list(WHAT)},
                "room": {"type": "string", "description": "A room saved in the measurements book."},
                "length": num, "width": num, "height": num,
                "unit": {"type": "string", "enum": ["m", "cm", "mm", "ft", "in"]},
                "area_m2": num, "run_m": {**num, "description": "Length of a fence or skirting run in metres."},
                "doors": {"type": "integer"}, "windows": {"type": "integer"}, "coats": {"type": "integer"},
                "include_ceiling": {"type": "boolean"}, "wastage_pct": num, "depth_mm": num,
                "tile_w_mm": num, "tile_h_mm": num, "joint_mm": num, "tile_thickness_mm": num,
                "pack_m2": {**num, "description": "Square metres per pack, box or turf roll."},
                "roll_width_m": num, "roll_length_m": num, "pattern_repeat_m": num,
                "panel_width_m": num, "board_w_mm": num, "board_length_m": num, "sheet_m2": num,
                "coverage_m2_per_litre": num, "bags_per_post": num,
            },
            "required": ["what"],
            "additionalProperties": False,
        },
    }]


NAMES = {"diy_calc"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    if args.get("what") not in CALCS:
        raise ValueError(f"I can't work out {args.get('what')}. Try: {', '.join(WHAT)}.")
    return calculate(settings, args["what"], args.get)
