"""Instagram highlight covers: the matching round icons under a business's bio (Prices, Reviews, Hours, Find us...).

make_highlight_covers draws one 1080x1920 cover per highlight, the size Instagram asks for, with a simple line icon
centred in the middle circle Instagram shows (everything important sits inside an 840px circle, so nothing is cut).
Icons are drawn as shapes, so they look the same on every phone and need no icon pack: star, clock, pin, menu, heart,
chat, tag, camera, bag, phone, scissors, home, gift, calendar and info; or give one to three letters instead. Styles:
solid (brand colour with a white or near-black icon, whichever reads better), outline (white with a brand ring and
icon) and tint (a soft brand tint with a brand icon). It saves 01-<label>.png ... in the order given, and
highlights-preview.png showing them as round bubbles with their labels, as on the profile, in
Kinetic Web Designs/<name>/posts/highlights.
"""

import math
import re

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_contrast import UI, colour, fix, ratio, rgb
from design_extract import FOLDER
from design_palette import on
from design_social import mix
from docs_tools import font

NAMES = {"make_highlight_covers"}
SIZE = (1080, 1920)
CIRCLE = 840  # Instagram shows about the middle 1080px circle; keep the ring and icon well inside it
MAX_COVERS = 12
STYLES = ("solid", "outline", "tint")
ICONS = ("star", "clock", "pin", "menu", "heart", "chat", "tag", "camera", "bag", "phone", "scissors", "home", "gift",
         "calendar", "info")
GUESS = {  # label words that suggest an icon
    "review": "star", "rating": "star", "testimonial": "star", "hour": "clock", "time": "clock", "open": "clock",
    "find": "pin", "location": "pin", "where": "pin", "visit": "pin", "map": "pin", "menu": "menu", "food": "menu",
    "love": "heart", "fav": "heart", "contact": "chat", "faq": "chat", "message": "chat", "dm": "chat", "price": "tag",
    "offer": "tag", "deal": "tag", "sale": "tag", "photo": "camera", "work": "camera", "gallery": "camera",
    "portfolio": "camera", "shop": "bag", "product": "bag", "store": "bag", "call": "phone", "phone": "phone",
    "cut": "scissors", "hair": "scissors", "barber": "scissors", "style": "scissors", "stay": "home", "room": "home",
    "home": "home", "gift": "gift", "voucher": "gift", "book": "calendar", "event": "calendar", "about": "info",
    "info": "info", "us": "info",
}


def guess(label: str) -> str:
    words = re.findall(r"[a-z]+", label.lower())
    for w in words:
        for key, icon in GUESS.items():
            if w.startswith(key):
                return icon
    return ""


def icon(d: ImageDraw.ImageDraw, kind: str, cx: float, cy: float, r: float, ink) -> None:
    """Draw a simple line icon about 2r wide, centred on (cx, cy)."""
    w = max(4, round(r * 0.14))  # line weight

    def ring(x, y, rr, width=w):
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=ink, width=width)

    def line(*pts, width=w):
        d.line(pts, fill=ink, width=width, joint="curve")
        for x, y in (pts[0], pts[-1]):
            d.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=ink)

    def shape(pts):
        line(*pts, pts[0], pts[1])  # closed, with rounded joins

    if kind == "star":
        shape([(cx + (r if i % 2 == 0 else r * 0.45) * math.cos(-math.pi / 2 + i * math.pi / 5),
                cy + r * 0.08 + (r if i % 2 == 0 else r * 0.45) * math.sin(-math.pi / 2 + i * math.pi / 5))
               for i in range(10)])
    elif kind == "clock":
        ring(cx, cy, r)
        line((cx, cy - r * 0.6), (cx, cy), (cx + r * 0.45, cy + r * 0.3))
    elif kind == "pin":
        top, rr = cy - r * 0.3, r * 0.65
        arc = [(cx + rr * math.cos(math.radians(a)), top + rr * math.sin(math.radians(a))) for a in range(150, 391, 10)]
        shape(arc + [(cx, cy + r)])
        ring(cx, top, rr * 0.36)
    elif kind == "menu":
        for dy in (-0.55, 0, 0.55):
            line((cx - r * 0.85, cy + r * dy), (cx + r * 0.85, cy + r * dy))
    elif kind == "heart":
        pts = []
        for i in range(60):
            t = 2 * math.pi * i / 60
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append((cx + x * r / 16, cy - y * r / 16 - r * 0.1))
        shape(pts)
    elif kind == "chat":
        d.rounded_rectangle((cx - r, cy - r * 0.75, cx + r, cy + r * 0.45), radius=r * 0.35, outline=ink, width=w)
        d.polygon([(cx - r * 0.45, cy + r * 0.45 - w / 2), (cx - r * 0.6, cy + r * 0.95), (cx - r * 0.05,
                                                                                      cy + r * 0.45 - w / 2)],
                  fill=ink)
        for dx in (-0.45, 0, 0.45):
            rr = w * 0.8
            d.ellipse((cx + r * dx - rr, cy - r * 0.15 - rr, cx + r * dx + rr, cy - r * 0.15 + rr), fill=ink)
    elif kind == "tag":
        pts = [(cx - r * 0.9, cy - r * 0.9), (cx + r * 0.05, cy - r * 0.9), (cx + r * 0.95, cy),
               (cx + r * 0.05, cy + r * 0.9), (cx - r * 0.9, cy + r * 0.9)]
        shape(pts)
        ring(cx - r * 0.45, cy - r * 0.45, r * 0.16)
    elif kind == "camera":
        d.rounded_rectangle((cx - r, cy - r * 0.55, cx + r, cy + r * 0.8), radius=r * 0.2, outline=ink, width=w)
        line((cx - r * 0.4, cy - r * 0.55), (cx - r * 0.25, cy - r * 0.8), (cx + r * 0.25, cy - r * 0.8),
             (cx + r * 0.4, cy - r * 0.55))
        ring(cx, cy + r * 0.12, r * 0.4)
    elif kind == "bag":
        d.rounded_rectangle((cx - r * 0.85, cy - r * 0.4, cx + r * 0.85, cy + r), radius=r * 0.12, outline=ink,
                            width=w)
        d.arc((cx - r * 0.4, cy - r, cx + r * 0.4, cy + r * 0.2), 180, 360, fill=ink, width=w)
    elif kind == "phone":
        d.rounded_rectangle((cx - r * 0.55, cy - r, cx + r * 0.55, cy + r), radius=r * 0.18, outline=ink, width=w)
        line((cx - r * 0.15, cy + r * 0.72), (cx + r * 0.15, cy + r * 0.72))
    elif kind == "scissors":
        ring(cx - r * 0.45, cy + r * 0.6, r * 0.3)
        ring(cx + r * 0.45, cy + r * 0.6, r * 0.3)
        line((cx - r * 0.3, cy + r * 0.35), (cx + r * 0.45, cy - r))
        line((cx + r * 0.3, cy + r * 0.35), (cx - r * 0.45, cy - r))
    elif kind == "home":
        line((cx - r, cy - r * 0.05), (cx, cy - r * 0.95), (cx + r, cy - r * 0.05))
        line((cx - r * 0.7, cy - r * 0.3), (cx - r * 0.7, cy + r * 0.9), (cx + r * 0.7, cy + r * 0.9),
             (cx + r * 0.7, cy - r * 0.3))
        line((cx - r * 0.2, cy + r * 0.9), (cx - r * 0.2, cy + r * 0.35), (cx + r * 0.2, cy + r * 0.35),
             (cx + r * 0.2, cy + r * 0.9))
    elif kind == "gift":
        d.rectangle((cx - r * 0.8, cy - r * 0.15, cx + r * 0.8, cy + r * 0.95), outline=ink, width=w)
        d.rectangle((cx - r * 0.95, cy - r * 0.5, cx + r * 0.95, cy - r * 0.15), outline=ink, width=w)
        line((cx, cy - r * 0.5), (cx, cy + r * 0.95))
        d.arc((cx - r * 0.6, cy - r * 0.95, cx, cy - r * 0.4), 140, 360, fill=ink, width=w)
        d.arc((cx, cy - r * 0.95, cx + r * 0.6, cy - r * 0.4), 180, 40, fill=ink, width=w)
    elif kind == "calendar":
        d.rounded_rectangle((cx - r * 0.9, cy - r * 0.7, cx + r * 0.9, cy + r * 0.9), radius=r * 0.15, outline=ink,
                            width=w)
        line((cx - r * 0.9, cy - r * 0.25), (cx + r * 0.9, cy - r * 0.25))
        line((cx - r * 0.45, cy - r * 0.95), (cx - r * 0.45, cy - r * 0.5))
        line((cx + r * 0.45, cy - r * 0.95), (cx + r * 0.45, cy - r * 0.5))
        rr = w * 0.9
        for dx in (-0.45, 0, 0.45):
            for dy in (0.15, 0.55):
                d.ellipse((cx + r * dx - rr, cy + r * dy - rr, cx + r * dx + rr, cy + r * dy + rr), fill=ink)
    elif kind == "info":
        ring(cx, cy, r)
        line((cx, cy - r * 0.1), (cx, cy + r * 0.5))
        rr = w * 0.9
        d.ellipse((cx - rr, cy - r * 0.45 - rr, cx + rr, cy - r * 0.45 + rr), fill=ink)


def cover(brand: str, style: str, kind: str, letters: str) -> Image.Image:
    tint = "#%02x%02x%02x" % mix(brand, "#ffffff", 0.86)
    if style == "solid":
        back, ink = rgb(brand), rgb(on(brand))
    elif style == "outline":
        back = (255, 255, 255)
        ink = rgb(brand if ratio(brand, "#ffffff") >= UI else fix(brand, "#ffffff", UI))
    else:
        back = rgb(tint)
        ink = rgb(brand if ratio(brand, tint) >= UI else fix(brand, tint, UI))
    image = Image.new("RGB", SIZE, back)
    d = ImageDraw.Draw(image)
    cx, cy = SIZE[0] / 2, SIZE[1] / 2
    if style == "outline":
        rr = CIRCLE / 2
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=ink, width=18)
    if letters:
        size = {1: 380, 2: 300, 3: 230}[len(letters)]
        d.text((cx, cy), letters, font=font(size, True), fill=ink, anchor="mm")
    else:
        icon(d, kind, cx, cy, CIRCLE * 0.27, ink)
    return image


def preview(covers: list[Image.Image], labels: list[str]) -> Image.Image:
    bubble, gap, pad = 180, 48, 60
    cols = min(len(covers), 6)
    rows = math.ceil(len(covers) / cols)
    sheet = Image.new("RGB", (pad * 2 + cols * bubble + (cols - 1) * gap, pad * 2 + rows * (bubble + 80)),
                      (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    mask = Image.new("L", (bubble, bubble), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, bubble - 1, bubble - 1), fill=255)
    for i, (image, label) in enumerate(zip(covers, labels)):
        x = pad + (i % cols) * (bubble + gap)
        y = pad + (i // cols) * (bubble + 80)
        side = SIZE[0]
        crop = image.crop((0, (SIZE[1] - side) // 2, side, (SIZE[1] + side) // 2)).resize((bubble, bubble),
                                                                                         Image.LANCZOS)
        d.ellipse((x - 8, y - 8, x + bubble + 8, y + bubble + 8), outline=(219, 219, 224), width=3)
        sheet.paste(crop, (x, y), mask)
        text = label if len(label) <= 14 else label[:13] + "…"
        d.text((x + bubble / 2, y + bubble + 22), text, font=font(26), fill=(24, 24, 27), anchor="mt")
    return sheet


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the highlight covers.")
    brand = colour(args.get("colour") or "")
    style = clean(args.get("style")).lower() or "solid"
    if style not in STYLES:
        raise ValueError(f"Pick a style: {', '.join(STYLES)}.")
    raw = args.get("highlights") or []
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_COVERS:
        raise ValueError(f"Give 1 to {MAX_COVERS} highlights, e.g. ['Prices', 'Reviews', 'Find us'].")
    items, guessed = [], []
    for item in raw:
        if isinstance(item, dict):
            label, kind, letters = clean(item.get("label")), clean(item.get("icon")).lower(), clean(item.get("text"))
        else:
            label, kind, letters = clean(item), "", ""
        if not label:
            raise ValueError("Each highlight needs a label, e.g. 'Reviews'.")
        letters = re.sub(r"\s", "", letters)
        if letters and len(letters) > 3:
            raise ValueError(f"Use 1 to 3 letters for '{label}' (or an icon).")
        if kind and kind not in ICONS:
            raise ValueError(f"Icons can be {', '.join(ICONS)}.")
        if not kind and not letters:
            kind = guess(label)
            if not kind:
                letters = label[0].upper()
                guessed.append(label)
        items.append((label, kind, letters))
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    posts = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/posts", create=True)
    path = posts / "highlights"
    path.mkdir(exist_ok=True)
    for old in path.glob("[0-9][0-9]-*.png"):
        old.unlink()  # a re-run with fewer highlights mustn't leave old covers behind
    covers, files = [], []
    for i, (label, kind, letters) in enumerate(items, start=1):
        image = cover(brand, style, kind, letters)
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:30] or "cover"
        file = f"{i:02d}-{slug}.png"
        image.save(path / file, optimize=True)
        covers.append(image)
        files.append(file)
    preview(covers, [label for label, _, _ in items]).save(path / "highlights-preview.png", optimize=True)
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made {len(files)} {style} highlight cover{'s' if len(files) != 1 else ''} for {name} in {where}: "
            f"{', '.join(files)}, plus highlights-preview.png to show the client. To use one: open the highlight on "
            "the profile, Edit highlight, Edit cover, and pick the picture from the camera roll."
            + (f" No icon matched {', '.join(repr(g) for g in guessed)}, so "
               f"{'it uses' if len(guessed) == 1 else 'they use'} the first letter; pick an icon if you'd like one."
               if guessed else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_highlight_covers",
        "description": "Make matching Instagram highlight covers (1080x1920, icon kept inside the round crop) in the "
                       "brand colour: a simple line icon per highlight (star, clock, pin, menu, heart, chat, tag, "
                       "camera, bag, phone, scissors, home, gift, calendar, info), guessed from the label if not "
                       "given, or 1-3 letters. Styles solid, outline or tint. Saves numbered PNGs and a preview in "
                       "Kinetic Web Designs/<name>/posts/highlights. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "style": {"type": "string", "enum": list(STYLES), "description": "Default solid."},
                "highlights": {"type": "array", "description": "1-12 labels, or {label, icon, text}.",
                               "items": {"anyOf": [{"type": "string"}, {"type": "object", "properties": {
                                   "label": {"type": "string"}, "icon": {"type": "string", "enum": list(ICONS)},
                                   "text": {"type": "string"}}, "required": ["label"]}]}},
            },
            "required": ["name", "colour", "highlights"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
