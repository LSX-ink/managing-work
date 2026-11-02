"""Menus and price lists: a one-page A4 or A5 list in the brand colour, for a barber's wall, a café counter or a salon.

make_price_list lays out sections (e.g. "Cuts", "Beard") of items with prices joined by dotted leaders and an optional
short note under each, with the business name in a brand-colour header and the address or web line at the bottom. It
uses two columns when there are many items and shrinks the type to fit the page, never below 8pt; if it still doesn't
fit, it says to split the list. Pages are drawn at 300 dpi with a 3mm bleed so a print shop can trim them. It saves
<slug>.pdf for printing, <slug>.png to post or show on a screen, in Kinetic Web Designs/<name>/print.
"""

import re

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio, rgb
from design_extract import FOLDER
from design_palette import on
from design_social import fit
from docs_tools import font

NAMES = {"make_price_list"}
DPI = 300
MM = DPI / 25.4
PAGES = {"A4": (210, 297), "A5": (148, 210)}
BLEED, MARGIN = round(3 * MM), round(14 * MM)
SMALLEST = round(8 / 72 * DPI)  # 8pt, the smallest a menu should go (33px)
INK, MUTED = (24, 24, 27), (82, 82, 91)
MAX_ITEMS = 80


def items_of(sections) -> list[dict]:
    if not isinstance(sections, list) or not sections:
        raise ValueError("Give the sections, e.g. a 'Cuts' section with items like 'Skin fade' at '£18'.")
    out = []
    for s in sections:
        if not isinstance(s, dict):
            raise ValueError("Each section needs a title and items.")
        rows = []
        for item in s.get("items") or []:
            if not isinstance(item, dict) or not str(item.get("name") or "").strip():
                raise ValueError("Each item needs a name (and usually a price).")
            rows.append({k: " ".join(str(item.get(k) or "").split()) for k in ("name", "price", "note")})
        if rows:
            out.append({"title": " ".join(str(s.get("title") or "").split()), "items": rows})
    count = sum(len(s["items"]) for s in out)
    if not count:
        raise ValueError("Add at least one item with a name and price.")
    if count > MAX_ITEMS:
        raise ValueError(f"That's {count} items; split it into two lists of up to {MAX_ITEMS}.")
    return out


def blocks(sections: list[dict], scale: float) -> list[tuple]:
    """('title' | 'item', data, height) in reading order at this type scale."""
    out = []
    for s in sections:
        if s["title"]:
            out.append(("title", s["title"], round(110 * scale)))
        for item in s["items"]:
            out.append(("item", item, round((64 + (50 if item["note"] else 0)) * scale)))
        out.append(("gap", None, round(40 * scale)))
    return out[:-1]


def columns(parts: list[tuple], count: int) -> list[list[tuple]]:
    """Split into `count` columns of about equal height, never leaving a section title at the bottom."""
    if count == 1:
        return [parts]
    total, run, split = sum(p[2] for p in parts), 0, len(parts)
    for i, p in enumerate(parts):
        if run + p[2] / 2 > total / 2:
            split = i
            break
        run += p[2]
    while split > 0 and parts[split - 1][0] in ("title", "gap"):
        split -= 1
    second = parts[split:]
    while second and second[0][0] == "gap":
        second = second[1:]
    return [parts[:split], second]


def draw_item(d: ImageDraw.ImageDraw, x: int, y: int, width: int, item: dict, scale: float, brand) -> None:
    size = round(44 * scale)
    f, bold = font(size), font(size, True)
    price = item["price"]
    price_w = d.textlength(price, font=bold) if price else 0
    room = width - price_w - (24 if price else 0)
    name = item["name"]
    while name and d.textlength(name, font=f) > room:
        name = name[:-2].rstrip() + "…"
    d.text((x, y), name, font=f, fill=INK)
    if price:
        d.text((x + width, y), price, font=bold, fill=brand, anchor="ra")
        start = x + d.textlength(name, font=f) + 16
        end = x + width - price_w - 16
        dot_y = y + round(size * 0.8)
        for dx in range(round(start), round(end), max(8, round(14 * scale))):
            d.ellipse((dx, dot_y, dx + 3, dot_y + 3), fill=(180, 180, 188))
    if item["note"]:
        _, rows = fit(d, item["note"], width, (round(32 * scale),), 1, False)
        d.text((x, y + round(60 * scale)), rows[0], font=font(round(32 * scale)), fill=MUTED)


def render(name: str, brand: str, sections: list[dict], footer: str, paper: str) -> Image.Image:
    w_mm, h_mm = PAGES[paper]
    size = (round(w_mm * MM) + 2 * BLEED, round(h_mm * MM) + 2 * BLEED)
    page_scale = 1.0 if paper == "A4" else 0.72
    image = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(image)
    header = round(420 * page_scale) + BLEED
    d.rectangle((0, 0, size[0], header), fill=rgb(brand))
    text = rgb(on(brand))
    inner = size[0] - 2 * (BLEED + MARGIN)
    big, rows = fit(d, name, inner, tuple(round(s * page_scale) for s in (150, 130, 110, 90)), 1, True)
    d.text((size[0] / 2, BLEED + (header - BLEED) / 2), rows[0], font=font(big, True), fill=text, anchor="mm")
    top, bottom = header + MARGIN, size[1] - BLEED - MARGIN - (round(70 * page_scale) if footer else 0)
    count = sum(len(s["items"]) for s in sections)
    cols = 2 if count > (14 if paper == "A4" else 10) else 1
    gutter = round(60 * page_scale)
    col_w = (inner - gutter * (cols - 1)) // cols
    scale = 1.9 * page_scale  # start big and shrink until it fits, so short lists fill the page
    while True:
        parts = columns(blocks(sections, scale), cols)
        if max(sum(p[2] for p in col) for col in parts) <= bottom - top:
            break
        scale -= 0.04
        if 44 * scale < SMALLEST:
            raise ValueError(f"That list doesn't fit on one {paper} page at a readable size; split it in two or "
                             "use A4.")
    accent = rgb(brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA))  # titles and prices read
    used = max(sum(p[2] for p in col) for col in parts)
    top += (bottom - top - used) // 3  # a short list sits a little above the middle, not stuck to the header
    for c, col in enumerate(parts):
        x, y = BLEED + MARGIN + c * (col_w + gutter), top
        for kind, data, height in col:
            if kind == "title":
                d.text((x, y + round(30 * scale)), data.upper(), font=font(round(48 * scale), True), fill=accent)
                d.line((x, y + round(96 * scale), x + col_w, y + round(96 * scale)),
                       fill=(214, 214, 220), width=max(2, round(3 * scale)))
            elif kind == "item":
                draw_item(d, x, y, col_w, data, scale, accent)
            y += height
    if footer:
        small, line = fit(d, footer, inner, (round(36 * page_scale),), 1, False)
        d.text((size[0] / 2, size[1] - BLEED - MARGIN), line[0], font=font(small), fill=MUTED, anchor="ms")
    return image


def run(settings: Settings, args: dict) -> str:
    name = " ".join(str(args.get("name") or "").split())
    if not name:
        raise ValueError("Give the business name for the price list.")
    brand = colour(args.get("colour") or "")
    sections = items_of(args.get("sections"))
    paper = str(args.get("paper") or "A4").upper()
    if paper not in PAGES:
        raise ValueError("Pick A4 or A5 paper.")
    footer = " ".join(str(args.get("footer") or "").split())
    slug = re.sub(r"[^a-z0-9]+", "-", str(args.get("title") or "price list").lower()).strip("-")[:40] or "price-list"
    page = render(name, brand, sections, footer, paper)
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/print", create=True)
    page.save(path / f"{slug}.pdf", "PDF", resolution=DPI)
    page.save(path / f"{slug}.png", dpi=(DPI, DPI), optimize=True)
    where = path.relative_to(memory.root(settings)).as_posix()
    count = sum(len(s["items"]) for s in sections)
    return (f"Made a {paper} price list for {name} with {count} item{'s' if count != 1 else ''} in "
            f"{len(sections)} section{'s' if len(sections) != 1 else ''}: {slug}.pdf to print (300 dpi, 3mm bleed) "
            f"and {slug}.png to post or show on a screen, in {where}.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_price_list",
        "description": "Make a one-page A4 or A5 price list or menu in the brand colour: business name header, "
                       "sections of items with dotted leaders to the prices and optional notes, a footer line, two "
                       "columns for long lists, never smaller than 8pt. Saves a print-ready PDF (3mm bleed) and a "
                       "PNG in Kinetic Web Designs/<name>/print. Use for barbers, salons, cafés and takeaways. Answer "
                       "in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (header and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "sections": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "title": {"type": "string", "description": "e.g. 'Cuts'"},
                        "items": {"type": "array", "items": {"type": "object", "properties": {
                            "name": {"type": "string"}, "price": {"type": "string", "description": "e.g. '£18'"},
                            "note": {"type": "string", "description": "Short line under it (optional)."}},
                            "required": ["name"]}}},
                        "required": ["items"]},
                },
                "paper": {"type": "string", "enum": ["A4", "A5"]},
                "footer": {"type": "string", "description": "Bottom line, e.g. address, phone or 'Book at ...'."},
                "title": {"type": "string", "description": "File name, e.g. 'menu' (default 'price list')."},
            },
            "required": ["name", "colour", "sections"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
