"""Starter logos and favicons for a brand, as clean SVG files.

make_logo draws four simple marks from a name and a brand colour: a rounded tile and a round badge with the initials,
an outline ring, and a wordmark (tile plus the name), with a white-text copy
of the wordmark for dark backgrounds. Text colour is picked for contrast with design_palette.on, so
the initials always read. It also writes favicon.svg (the tile, sized for browser tabs) and logos.html to compare them
side by side on light and dark. Files go in Kinetic Web Designs/<name>/logo, next to the brand kit. They are a solid
starting point for a client or a placeholder until a designer's logo arrives, not a finished identity.
"""

import re
from xml.sax.saxutils import escape

import memory
from config import Settings
from design_contrast import colour
from design_extract import FOLDER
from design_palette import on

NAMES = {"make_logo"}
STYLES = ("tile", "badge", "outline", "wordmark")
FONT = "Inter, 'Segoe UI', system-ui, -apple-system, Arial, sans-serif"
SMALL_WORDS = {"and", "of", "the", "&", "a", "an", "for"}


def initials(name: str, given: str = "") -> str:
    if given:
        letters = re.sub(r"[^\w]", "", given)[:2].upper()
        if letters:
            return letters
    words = [w for w in re.findall(r"[A-Za-z0-9][\w']*", name)]
    words = [w for w in words if w.lower() not in SMALL_WORDS] or words
    if not words:
        raise ValueError("Give a name with at least one letter or number.")
    if len(words) == 1:
        return words[0][:2].upper() if len(words[0]) > 1 else words[0].upper()
    return (words[0][0] + words[1][0]).upper()


def font_size(text: str, box: int) -> int:
    return round(box * (0.46 if len(text) > 1 else 0.56))


def letters(text: str, x: float, y: float, size: int, fill: str, weight: int = 700) -> str:
    return (f'<text x="{x:g}" y="{y:g}" text-anchor="middle" dominant-baseline="central" font-family="{FONT}" '
            f'font-size="{size}" font-weight="{weight}" letter-spacing="-0.02em" fill="{fill}">{escape(text)}</text>')


def svg(width: int, height: int, body: str, label: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{escape(label, {chr(34): "&quot;"})}">{body}</svg>\n')


def tile(mark: str, brand: str, label: str, box: int = 256) -> str:
    radius = round(box * 0.22)
    return svg(box, box, f'<rect width="{box}" height="{box}" rx="{radius}" fill="{brand}"/>'
               + letters(mark, box / 2, box / 2, font_size(mark, box), on(brand)), label)


def badge(mark: str, brand: str, label: str, box: int = 256) -> str:
    return svg(box, box, f'<circle cx="{box / 2:g}" cy="{box / 2:g}" r="{box / 2:g}" fill="{brand}"/>'
               + letters(mark, box / 2, box / 2, font_size(mark, box), on(brand)), label)


def outline(mark: str, brand: str, label: str, box: int = 256) -> str:
    stroke = round(box * 0.06)
    r = box / 2 - stroke / 2
    return svg(box, box, f'<circle cx="{box / 2:g}" cy="{box / 2:g}" r="{r:g}" fill="none" stroke="{brand}" '
               f'stroke-width="{stroke}"/>' + letters(mark, box / 2, box / 2, font_size(mark, box) - 8, brand), label)


def wordmark(mark: str, name: str, brand: str, text_colour: str, label: str) -> str:
    height, box = 96, 72
    gap = 20
    width = round(box + gap + max(4, len(name)) * 26 + 24)  # roomy: bold 40px is about 25px a letter
    pad = (height - box) / 2
    body = (f'<rect x="{pad:g}" y="{pad:g}" width="{box}" height="{box}" rx="16" fill="{brand}"/>'
            + letters(mark, pad + box / 2, height / 2, font_size(mark, box), on(brand))
            + f'<text x="{pad + box + gap:g}" y="{height / 2:g}" dominant-baseline="central" font-family="{FONT}" '
              f'font-size="40" font-weight="700" letter-spacing="-0.02em" fill="{text_colour}">{escape(name)}</text>')
    return svg(width + round(pad), height, body, label)


def cards(files: list[str]) -> str:
    return "".join(f'<figure><img src="{f}" alt="{escape(f)}"><figcaption>{escape(f)}</figcaption></figure>'
                   for f in files)


def preview(name: str, files: list[str]) -> str:
    light = [f for f in files if not f.endswith("-dark.svg")]
    dark = [f for f in files if f.replace(".svg", "-dark.svg") not in files]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(name)} logos</title><link rel="icon" href="favicon.svg">
<style>
body {{ margin: 0; font-family: system-ui, sans-serif; }}
section {{ padding: 32px 24px; display: flex; flex-wrap: wrap; gap: 24px; align-items: center; }}
.dark {{ background: #111; color: #eee; }}
figure {{ margin: 0; text-align: center; }}
img {{ height: 96px; max-width: 100%; }}
figcaption {{ font-size: 12px; opacity: 0.7; margin-top: 8px; }}
</style></head>
<body><section>{cards(light)}</section><section class="dark">{cards(dark)}</section></body></html>
"""


def build(settings: Settings, args: dict) -> str:
    name = str(args.get("name") or "").strip()
    if not name:
        raise ValueError("Give the brand or client a name for the logo.")
    brand = colour(args.get("colour") or "")
    mark = initials(name, str(args.get("initials") or ""))
    text_colour = colour(args.get("text_colour") or "#111111")
    wanted = [s for s in (args.get("styles") or STYLES) if s in STYLES] or list(STYLES)
    folder_name = memory.safe_name(name, "folder name")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{folder_name}/logo", create=True)
    made = []
    makers = {"tile": lambda: tile(mark, brand, name), "badge": lambda: badge(mark, brand, name),
              "outline": lambda: outline(mark, brand, name),
              "wordmark": lambda: wordmark(mark, name, brand, text_colour, name)}
    for style in wanted:
        (path / f"logo-{style}.svg").write_text(makers[style](), encoding="utf-8")
        made.append(f"logo-{style}.svg")
    if "wordmark" in wanted:  # the name in white, for dark backgrounds
        (path / "logo-wordmark-dark.svg").write_text(wordmark(mark, name, brand, "#ffffff", name), encoding="utf-8")
        made.append("logo-wordmark-dark.svg")
    (path / "favicon.svg").write_text(tile(mark, brand, name, 64), encoding="utf-8")
    (path / "logos.html").write_text(preview(name, made + ["favicon.svg"]), encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made {len(made)} starter logo files for {name} with the initials {mark} in {brand} ({', '.join(made)}), "
            f"plus favicon.svg, in {where}. Open logos.html to compare them on light and dark. Add the favicon with "
            f'<link rel="icon" href="favicon.svg">. These are simple starting marks; a custom logo can replace them '
            "later.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_logo",
        "description": "Make simple starter logos for a brand or client as SVG files: a rounded tile and round badge "
                       "with the initials, an outline ring and a wordmark, plus favicon.svg and logos.html to compare "
                       "them on light and dark. Uses the brand colour with readable text. Saves in Kinetic Web "
                       "Designs/<name>/logo, next to make_brand_kit's files. Say they are starting marks, not a "
                       "finished identity. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Brand or client name."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "initials": {"type": "string", "description": "1-2 letters to use instead of the name's initials."},
                "text_colour": {"type": "string", "description": "Wordmark name colour (default near-black)."},
                "styles": {"type": "array", "items": {"type": "string", "enum": list(STYLES)}},
            },
            "required": ["name", "colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return build(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
