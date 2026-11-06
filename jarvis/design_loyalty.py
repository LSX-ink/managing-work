"""Loyalty stamp cards: "buy 9, get the 10th free" cards for cafés, barbers and salons, ready for the printer.

make_loyalty_card draws a business-card-size (85 x 55mm) stamp card at 300 dpi with 3mm bleed, words kept 4mm inside
the cut and never below 7pt, the same as make_business_card so they can go in one print order. The front is the brand
colour with the business name and "Loyalty card"; the back has a row or two of stamp circles (4 to 12), the last one
filled in the brand colour and marked FREE, the reward written out ("10th coffee free"), and a name line. Circles are
at least 7mm across so a rubber stamp or a pen tick fits. It saves loyalty.pdf (front and back), PNGs of each side and
loyalty-preview.png, in Kinetic Web Designs/<name>/print.
"""

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_cards import BLEED, DPI, INK, MM, MUTED, SAFE, SIZE, TRIM, fit, front, preview
from design_contrast import AA, colour, fix, ratio, rgb
from design_extract import FOLDER
from design_palette import on
from docs_tools import font

NAMES = {"make_loyalty_card"}
MIN_STAMPS, MAX_STAMPS = 4, 12
SMALLEST_CIRCLE = round(7 * MM)  # room for a rubber stamp or a tick


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def grid(stamps: int) -> tuple[int, int]:
    """(columns, rows): one row up to 6 stamps, otherwise two even-ish rows."""
    if stamps <= 6:
        return stamps, 1
    return (stamps + 1) // 2, 2


def back(brand: str, stamps: int, reward: str, name_line: bool) -> tuple[Image.Image, list[str]]:
    image = Image.new("RGB", SIZE, (255, 255, 255))
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, SIZE[0], BLEED + 14), fill=rgb(brand))
    accent = rgb(brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA))
    left, right = BLEED + SAFE, SIZE[0] - BLEED - SAFE
    width = right - left
    cuts = []
    size, text, cut = fit(d, reward, width, 48, True)
    d.text((SIZE[0] / 2, BLEED + SAFE + 30), text, font=font(size, True), fill=INK, anchor="mt")
    cuts += ["the reward"] if cut else []
    cols, rows = grid(stamps)
    top = BLEED + SAFE + 30 + size + 34
    bottom = SIZE[1] - BLEED - SAFE - (70 if name_line else 10)
    gap = 22
    circle = min((width - gap * (cols - 1)) // cols, (bottom - top - gap * (rows - 1)) // rows, 150)
    if circle < SMALLEST_CIRCLE:
        raise ValueError(f"{stamps} stamps don't fit at a stampable size; use {MAX_STAMPS} or fewer.")
    used_h = rows * circle + (rows - 1) * gap
    y0 = top + (bottom - top - used_h) // 2
    n = 0
    for r in range(rows):
        in_row = cols if r < rows - 1 else stamps - cols * (rows - 1)
        row_w = in_row * circle + (in_row - 1) * gap
        x0 = (SIZE[0] - row_w) // 2
        for c in range(in_row):
            n += 1
            x, y = x0 + c * (circle + gap), y0 + r * (circle + gap)
            box = (x, y, x + circle, y + circle)
            if n == stamps:
                d.ellipse(box, fill=rgb(brand), outline=accent, width=4)
                d.text((x + circle / 2, y + circle / 2), "FREE", font=font(max(30, circle // 4), True),
                       fill=rgb(on(brand)), anchor="mm")
            else:
                d.ellipse(box, outline=(170, 170, 178), width=4)
                d.text((x + circle / 2, y + circle / 2), str(n), font=font(max(30, circle // 4)),
                       fill=(200, 200, 206), anchor="mm")
    if name_line:
        y = SIZE[1] - BLEED - SAFE - 14
        d.text((left, y), "Name", font=font(30), fill=MUTED, anchor="ls")
        d.line((left + 100, y, right, y), fill=(190, 190, 198), width=3)
    return image, cuts


def run(settings: Settings, args: dict) -> str:
    clean = lambda k: " ".join(str(args.get(k) or "").split())  # noqa: E731
    business = clean("name")
    if not business:
        raise ValueError("Give the business name for the loyalty card.")
    brand = colour(args.get("colour") or "")
    stamps = int(args.get("stamps") or 10)
    if not MIN_STAMPS <= stamps <= MAX_STAMPS:
        raise ValueError(f"Use between {MIN_STAMPS} and {MAX_STAMPS} stamps (10 is the usual).")
    item = clean("item") or "visit"
    reward = clean("reward") or f"Your {ordinal(stamps)} {item} is free"
    if len(reward) > 50:
        raise ValueError("Keep the reward short, e.g. '10th coffee free' (50 letters at most).")
    tagline = clean("tagline") or "Loyalty card"
    name_line = args.get("name_line", True) is not False
    first, cut_front = front(brand, business, tagline)
    second, cut_back = back(brand, stamps, reward, name_line)
    cuts = cut_front + cut_back
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(business, 'folder name')}/print", create=True)
    first.save(path / "loyalty-front.png", dpi=(DPI, DPI))
    second.save(path / "loyalty-back.png", dpi=(DPI, DPI))
    first.save(path / "loyalty.pdf", "PDF", resolution=DPI, save_all=True, append_images=[second])
    preview([first, second]).save(path / "loyalty-preview.png", optimize=True)
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made a {stamps}-stamp loyalty card for {business} in {where} (\"{reward}\"): loyalty.pdf (front and "
            "back) to upload to a printer such as Moo or Vistaprint, loyalty-front.png and loyalty-back.png, and "
            "loyalty-preview.png to show the client. It's 85 x 55mm with 3mm bleed at 300 dpi, the same size as "
            "their business cards, so both can go in one order. Matt or uncoated card takes stamps and pen best."
            + (f" Heads up: {', '.join(cuts)} didn't fit at 7pt and {'was' if len(cuts) == 1 else 'were'} "
               "shortened." if cuts else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_loyalty_card",
        "description": "Make a print-ready loyalty stamp card (85 x 55mm, 3mm bleed, 300 dpi, business-card size): "
                       "front in the brand colour with the business name, back with 4-12 stamp circles, the last "
                       "marked FREE, the reward written out and a name line. Saves loyalty.pdf, PNGs and a preview "
                       "in Kinetic Web Designs/<name>/print. Use for cafés, barbers, salons and takeaways. Answer in "
                       "plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (front and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "stamps": {"type": "integer", "minimum": 4, "maximum": 12, "description": "Default 10."},
                "item": {"type": "string", "description": "What's free, e.g. 'coffee' or 'haircut' (default visit)."},
                "reward": {"type": "string", "description": "Reward line instead, e.g. 'Free cut after 8 visits'."},
                "tagline": {"type": "string", "description": "Front line under the name (default 'Loyalty card')."},
                "name_line": {"type": "boolean", "description": "Line for the customer's name (default yes)."},
            },
            "required": ["name", "colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
