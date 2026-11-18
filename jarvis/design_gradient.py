"""Smooth gradients for hero sections, buttons and backgrounds, without the muddy grey middle.

make_gradient blends 2 to 5 colours in OKLCH, the colour space that matches how eyes see, then writes the blend as
many CSS colour stops so every browser shows the smooth version (a plain CSS gradient between, say, blue and orange
goes through dull grey). Styles: linear (at an angle), radial, and aurora (soft glowing blobs, as on modern landing
pages). It checks whether white or near-black words stay readable across the whole gradient and says which to use.
With a name it saves gradient.css, gradient.html (a hero preview) and PNG backgrounds sized for a website, a phone
and a square post in Kinetic Web Designs/<name>/gradients.
"""

import html
import math

from PIL import Image, ImageDraw, ImageFilter

import memory
from config import Settings
from design_contrast import AA, LARGE_AA, colour, ratio, rgb
from design_extract import FOLDER

NAMES = {"make_gradient"}
STYLES = ("linear", "radial", "aurora")
SIZES = {"web": (1920, 1080), "phone": (1080, 1920), "square": (1080, 1080)}
STEPS = 8  # extra stops between each pair of colours
WHITE, INK = "#ffffff", "#0b0b0f"


def to_linear(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def from_linear(c: float) -> int:
    c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return max(0, min(255, round(c * 255)))


def oklab(hex_: str) -> tuple[float, float, float]:
    r, g, b = (to_linear(c) for c in rgb(hex_))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def from_oklab(lab: tuple[float, float, float]) -> str:
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return "#" + "".join(f"{from_linear(c):02x}" for c in (r, g, bl))


def mix(a: str, b: str, t: float) -> str:
    """t of the way from a to b in OKLCH: lightness and colourfulness change evenly and the hue turns the short way
    round the colour wheel, so blue to orange passes through bright pink rather than dull grey."""
    (l1, a1, b1), (l2, a2, b2) = oklab(a), oklab(b)
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1, h2 = math.atan2(b1, a1), math.atan2(b2, a2)
    if c1 < 0.02:  # a grey has no real hue, so borrow the other colour's
        h1 = h2
    if c2 < 0.02:
        h2 = h1
    turn = (h2 - h1 + math.pi) % (2 * math.pi) - math.pi
    hue, chroma = h1 + turn * t, c1 + (c2 - c1) * t
    return from_oklab((l1 + (l2 - l1) * t, chroma * math.cos(hue), chroma * math.sin(hue)))


def ramp(colours: list[str], steps: int = STEPS) -> list[str]:
    """The colours with `steps` OKLCH blends between each pair."""
    out = [colours[0]]
    for a, b in zip(colours, colours[1:]):
        out += [mix(a, b, i / (steps + 1)) for i in range(1, steps + 1)] + [b]
    return out


def stops(points: list[str]) -> str:
    last = len(points) - 1
    return ", ".join(f"{c} {i / last * 100:.4g}%" for i, c in enumerate(points))


def text_colour(points: list[str]) -> dict:
    """Which of white or near-black reads on every part of the gradient, and how well."""
    white, ink = min(ratio(WHITE, p) for p in points), min(ratio(INK, p) for p in points)
    best, worst = (WHITE, white) if white >= ink else (INK, ink)
    level = "all text" if worst >= AA else "big headings only" if worst >= LARGE_AA else "no text without a backing"
    return {"colour": best, "ratio": worst, "use": level}


def aurora_css(colours: list[str], base: str) -> str:
    spots = ["20% 20%", "80% 30%", "30% 85%", "85% 85%", "50% 50%"]
    layers = [f"radial-gradient(60% 60% at {spots[i]}, {c} 0%, transparent 70%)" for i, c in enumerate(colours)]
    return ", ".join(layers) + f", {base}"


def build(colours: list, style: str = "linear", angle: float = 135) -> dict:
    style = str(style or "linear").lower()
    if style not in STYLES:
        raise ValueError(f"Pick a style: {', '.join(STYLES)}.")
    if not isinstance(colours, list) or not 2 <= len(colours) <= 5:
        raise ValueError("Give 2 to 5 colours, e.g. ['#7c3aed', '#f97316'].")
    picked = [colour(c) for c in colours]
    points = ramp(picked)
    angle = float(angle) % 360
    if style == "linear":
        value = f"linear-gradient({angle:g}deg, {stops(points)})"
    elif style == "radial":
        value = f"radial-gradient(circle at 50% 40%, {stops(points)})"
    else:
        base = mix(picked[0], picked[-1], 0.5)
        value = aurora_css(picked, base)
        points = ramp([*picked, base], 4)
    return {"colours": picked, "style": style, "angle": angle, "css": value, "points": points,
            "text": text_colour(points)}


def draw(g: dict, size: tuple[int, int]) -> Image.Image:
    w, h = size
    points = g["points"]
    if g["style"] == "aurora":
        image = Image.new("RGB", size, rgb(points[-1]))
        d = ImageDraw.Draw(image)
        spots = [(0.2, 0.2), (0.8, 0.3), (0.3, 0.85), (0.85, 0.85), (0.5, 0.5)]
        r = 0.34 * max(w, h)
        for (x, y), c in reversed(list(zip(spots, g["colours"]))):  # the first colour ends on top, as in the CSS
            d.ellipse((x * w - r, y * h - r, x * w + r, y * h + r), fill=rgb(c))
        return image.filter(ImageFilter.GaussianBlur(max(w, h) / 6))
    line = ramp(g["colours"], 48)
    if g["style"] == "radial":
        image = Image.new("RGB", size, rgb(line[-1]))
        d = ImageDraw.Draw(image)
        cx, cy, far = w / 2, h * 0.4, math.hypot(w / 2, h * 0.6)
        for i in range(len(line) - 1, -1, -1):
            r = far * i / (len(line) - 1)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgb(line[i]))
        return image.filter(ImageFilter.GaussianBlur(4))
    # linear: the CSS gradient line (as long as the box measured along the angle), padded with the end colours
    # out to the diagonal, then turned to the angle (0deg points up, 90deg to the right) and cut to size
    turn = math.radians(g["angle"])
    length = max(2, round(abs(w * math.sin(turn)) + abs(h * math.cos(turn))))
    span = math.ceil(math.hypot(w, h)) + 2
    strip = Image.new("RGB", (len(line), 1))
    strip.putdata([rgb(c) for c in line])
    band = Image.new("RGB", (span, 1), rgb(line[0]))
    band.paste(Image.new("RGB", (span - (span - length) // 2, 1), rgb(line[-1])), ((span - length) // 2, 0))
    band.paste(strip.resize((length, 1), Image.BILINEAR), ((span - length) // 2, 0))
    turned = band.resize((span, span)).rotate(90 - g["angle"], resample=Image.BICUBIC)
    left, top = (span - w) // 2, (span - h) // 2
    return turned.crop((left, top, left + w, top + h))


def preview(g: dict, name: str) -> str:
    t = g["text"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(name)} gradient</title><link rel="stylesheet" href="gradient.css">
<style>
body {{ margin: 0; font-family: system-ui, sans-serif; background: #fff; color: #111; }}
.hero {{ min-height: 70vh; display: grid; place-content: center; text-align: center; padding: 48px 24px;
  color: {t['colour']}; }}
.hero h1 {{ font-size: clamp(2.2rem, 6vw, 4.5rem); margin: 0 0 12px; letter-spacing: -0.02em; }}
.row {{ display: flex; flex-wrap: wrap; gap: 16px; padding: 24px; align-items: center; }}
.chip {{ width: 64px; height: 64px; border-radius: 12px; }}
.btn {{ border: 0; border-radius: 999px; padding: 14px 28px; font: inherit; font-weight: 600;
  color: {t['colour']}; }}
</style></head>
<body><section class="hero gradient"><h1>{html.escape(name)}</h1><p>Words in {t['colour']}: at least
{t['ratio']:.1f}:1 everywhere, fine for {t['use']}.</p></section>
<div class="row">{''.join(f'<div class="chip" style="background:{c}" title="{c}"></div>' for c in g['colours'])}
<button class="btn gradient">A gradient button</button></div></body></html>
"""


def save(settings: Settings, g: dict, name: str) -> tuple[str, list[str]]:
    name = memory.safe_name(name, "folder name")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{name}/gradients", create=True)
    (path / "gradient.css").write_text(
        f"/* {g['style']} gradient by Alfred, blended in OKLCH so the middle stays bright. */\n"
        f":root {{ --gradient: {g['css']}; }}\n.gradient {{ background: var(--gradient); }}\n", encoding="utf-8")
    (path / "gradient.html").write_text(preview(g, name), encoding="utf-8")
    made = []
    for label, size in SIZES.items():
        draw(g, size).save(path / f"gradient-{label}.png", optimize=True)
        made.append(f"gradient-{label}.png")
    return path.relative_to(memory.root(settings)).as_posix(), made


def summary(g: dict, where: str = "", made: list[str] = ()) -> str:
    t = g["text"]
    shape = f"{g['angle']:g} degree linear" if g["style"] == "linear" else g["style"]
    article = "an" if shape[0] in "aeiou" else "a"
    text = (f"Made {article} {shape} gradient from {', '.join(g['colours'])}, blended in OKLCH so the middle stays "
            f"bright instead of going grey. Use {'white' if t['colour'] == WHITE else 'near-black'} words on it "
            f"({t['ratio']:.1f}:1 at the weakest point, fine for {t['use']}).")
    if where:
        text += (f" Saved gradient.css, gradient.html and {', '.join(made)} in {where}; open gradient.html to see "
                 "it as a hero.")
    else:
        text += f"\nCSS: background: {g['css']};"
    return text


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_gradient",
        "description": "Make a smooth gradient from 2-5 colours, blended in OKLCH so it doesn't go muddy grey in the "
                       "middle: linear (with an angle), radial, or aurora (soft glowing blobs). Says whether white or "
                       "dark words stay readable across it. With a name, saves gradient.css, a hero preview and PNG "
                       "backgrounds for web, phone and square posts in Kinetic Web Designs/<name>/gradients. Use for "
                       "hero sections, buttons, social posts and wallpapers. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "colours": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5,
                            "description": "2 to 5 colours, e.g. ['#7c3aed', '#f97316']."},
                "style": {"type": "string", "enum": list(STYLES)},
                "angle": {"type": "number", "description": "Linear angle in degrees (CSS: 90 = left to right)."},
                "name": {"type": "string", "description": "Brand or client folder to save in (optional)."},
            },
            "required": ["colours"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        g = build(args.get("colours"), args.get("style") or "linear", args.get("angle", 135))
        if args.get("name"):
            where, made = save(settings, g, str(args["name"]))
            return summary(g, where, made)
        return summary(g)
    except (TypeError, ValueError) as e:
        return str(e)
