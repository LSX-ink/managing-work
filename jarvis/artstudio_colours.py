"""Colours for artists: palettes from a base colour (colour-wheel maths), palettes taken from a picture, and the
nearest named colour for a hex code. Swatches pop up in an "art-palette" window; click one to copy its hex.
"""

import colorsys

from PIL import Image

import artstudio_common as ac
import screen
from config import Settings

KIND = "art-palette"
screen.EXTRA_KINDS.add(KIND)

SCHEMES = ("complementary", "analogous", "triadic", "tetradic", "split_complementary", "monochrome")
PICTURE_COLOURS = 6


def to_rgb(hex_code: str) -> tuple[int, int, int]:
    h = hex_code.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def to_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, int(c + 0.5 + 1e-6))):02x}" for c in rgb)  # halves round up


def hls_hex(h: float, lightness: float, s: float) -> str:
    return to_hex(c * 255 for c in colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, lightness)), s))


def scheme(base: str, name: str) -> list[str]:
    """The palette for a colour-wheel scheme, base colour first."""
    h, lightness, s = colorsys.rgb_to_hls(*(c / 255 for c in to_rgb(base)))
    turn = lambda deg: hls_hex(h + deg / 360, lightness, s)  # noqa: E731
    if name == "complementary":
        return [base, turn(180), hls_hex(h, lightness + (1 - lightness) * 0.5, s),
                hls_hex(h + 0.5, lightness * 0.6, s)]
    if name == "analogous":
        return [turn(-60), turn(-30), base, turn(30), turn(60)]
    if name == "triadic":
        return [base, turn(120), turn(240)]
    if name == "tetradic":
        return [base, turn(90), turn(180), turn(270)]
    if name == "split_complementary":
        return [base, turn(150), turn(210)]
    if name == "monochrome":
        return [hls_hex(h, level, s) for level in (0.15, 0.3, 0.45, 0.6, 0.75, 0.9)]
    raise ValueError(f"I know these palettes: {', '.join(s.replace('_', ' ') for s in SCHEMES)}.")


def distance(a: tuple, b: tuple) -> float:
    """How different two colours look ("redmean", a cheap perceptual weighting)."""
    r = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return ((2 + r / 256) * dr * dr + 4 * dg * dg + (2 + (255 - r) / 256) * db * db) ** 0.5


def nearest_name(hex_code: str) -> tuple[str, bool]:
    """(the closest CSS colour name, whether it's an exact match)."""
    rgb = to_rgb(hex_code)
    name = min(ac.NAMED, key=lambda n: distance(rgb, to_rgb(ac.NAMED[n])))
    return name, ac.NAMED[name] == hex_code


def swatch(hex_code: str, share: float | None = None) -> dict:
    out = {"hex": hex_code, "name": nearest_name(hex_code)[0]}
    if share is not None:
        out["share"] = round(share)
    return out


def palette_card(title: str, card_id: str, swatches: list[dict], buttons=None) -> dict:
    return screen.card(KIND, title, card_id, buttons=buttons, data={"swatches": swatches})


def make_palette(base: str, name: str) -> screen.Shown:
    colours = scheme(base, name)
    label = name.replace("_", " ")
    others = [{"label": s.replace("_", " ").title(), "say": f"Make a {s.replace('_', ' ')} palette from {base}."}
              for s in SCHEMES if s != name][:4]
    c = palette_card(f"{label.title()} palette", "art-palette", [swatch(h) for h in colours], others)
    return screen.Shown(f"Here's a {label} palette from {base}: {', '.join(colours)}.", c)


def picture_colours(im: Image.Image, count: int = PICTURE_COLOURS) -> list[tuple[str, float]]:
    """The main colours of a picture, biggest share first: [(hex, percent), ...]."""
    small = ac.rgb(im).copy()
    small.thumbnail((200, 200))
    quant = small.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    palette = quant.getpalette()[:count * 3]
    counts = sorted(quant.getcolors(count) or [], reverse=True)
    total = sum(n for n, _ in counts) or 1
    return [(to_hex(palette[i * 3:i * 3 + 3]), n * 100 / total) for n, i in counts]


def picture_palette(settings: Settings, folder: str, filename: str) -> screen.Shown:
    path, im = ac.load(settings, folder, filename)
    found = picture_colours(im)
    swatches = [swatch(h, share) for h, share in found]
    c = palette_card(f"Colours of {path.name}", f"art-palette-{path.name}", swatches,
                     [{"label": "Show picture", "say": f"Show me the file {path.name} from {path.parent.name}."}])
    names = ", ".join(s["name"] for s in swatches[:3])
    return screen.Shown(f"The main colours in {path.name} are {names}.", c)


def colour_name(value: str) -> screen.Shown:
    hex_code = ac.hex_colour(value)
    name, exact = nearest_name(hex_code)
    said = f"{hex_code} is {name}." if exact else f"{hex_code} is closest to {name}, which is {ac.NAMED[name]}."
    swatches = [{"hex": hex_code, "name": "yours"}, {"hex": ac.NAMED[name], "name": name}] if not exact else \
        [{"hex": hex_code, "name": name}]
    return screen.Shown(said, palette_card(f"Colour {hex_code}", "art-colour-name", swatches))


def tool_definitions() -> list[dict]:
    return [{
        "name": "art_colours",
        "description": "Colour palettes and colour names for art and design, shown as swatches that copy their hex "
                       "code when clicked. action 'palette' makes a colour scheme from a base colour: complementary, "
                       "analogous, triadic, tetradic, split_complementary or monochrome; 'picture_palette' takes the "
                       "six main colours from a photo or picture in the memory folders; 'colour_name' says the "
                       "nearest named colour for a hex code (or the hex for a colour name).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["palette", "picture_palette", "colour_name"]},
                "colour": {"type": "string", "description": "A hex code like #3fa9ff or a colour name like teal."},
                "scheme": {"type": "string", "enum": list(SCHEMES)},
                "folder": {"type": "string", "description": "picture_palette: memory folder, e.g. Personal."},
                "filename": {"type": "string", "description": "picture_palette: the picture's name or part of it."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"art_colours"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> screen.Shown:
    action = args.get("action")
    if action == "palette":
        return make_palette(ac.hex_colour(args.get("colour")), args.get("scheme") or "complementary")
    if action == "picture_palette":
        return picture_palette(settings, args.get("folder") or "", args.get("filename") or "")
    if action == "colour_name":
        return colour_name(args.get("colour"))
    raise ValueError("Pick palette, picture_palette or colour_name.")
