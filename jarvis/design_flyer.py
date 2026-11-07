"""Flyers: an A5 or A4 one-sided leaflet in the brand colour, for letterboxes, counters and noticeboards.

make_flyer lays out the business name, a big headline (an offer or opening news), a short line, up to five bullet
points with brand-colour dots, a call-to-action button, contact lines and an optional QR code to the website. With a
photo from a memory folder, the top of the page is the photo (turned the right way up) with the name on a brand band
under it; without one, the top is a brand-colour block. Type shrinks to fit but never below 9pt, the size people can
read at arm's length; if it still doesn't fit, it says what to shorten. Pages are 300 dpi with 3mm bleed. It saves
<slug>.pdf for printing and <slug>.png to post online, in Kinetic Web Designs/<name>/print.
"""

import re

from PIL import Image, ImageDraw, ImageOps

import memory
from config import Settings
from design_cards import qr_picture
from design_contrast import AA, colour, fix, ratio, rgb
from design_extract import FOLDER
from design_palette import on
from design_posts import load
from design_social import fit, wrap
from docs_tools import font

NAMES = {"make_flyer"}
DPI = 300
MM = DPI / 25.4
PAGES = {"A5": (148, 210), "A4": (210, 297)}
BLEED, MARGIN = round(3 * MM), round(12 * MM)
SMALLEST = round(9 / 72 * DPI)  # 9pt, readable at arm's length (38px)
INK, MUTED = (24, 24, 27), (82, 82, 91)
MAX_BULLETS = 5


def body(width: int, k: float, accent, brand: str, headline: str, line: str, bullets: list[str], cta: str,
         contact: list[str], qr: Image.Image | None, scale: float) -> Image.Image:
    """Everything under the top block, drawn on its own canvas so it can be measured and centred."""
    canvas = Image.new("RGB", (width, 6000), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    s = lambda v: max(SMALLEST, round(v * k * scale))  # noqa: E731
    y = 0
    hsize, rows = fit(d, headline, width, (s(120), s(104), s(90), s(78)), 3, True)
    for row in rows:
        d.text((0, y), row, font=font(hsize, True), fill=INK)
        y += round(hsize * 1.1)
    if line:
        y += s(24)
        for row in wrap(d, line, s(50), width, False)[:3]:
            d.text((0, y), row, font=font(s(50)), fill=MUTED)
            y += round(s(50) * 1.35)
    if bullets:
        y += s(40)
        dot = s(18)
        for b in bullets:
            rows = wrap(d, b, s(48), width - dot * 3, False)
            d.ellipse((0, y + s(48) // 2 - dot // 2, dot, y + s(48) // 2 + dot // 2), fill=accent)
            for row in rows:
                d.text((dot * 3, y), row, font=font(s(48)), fill=INK)
                y += round(s(48) * 1.3)
            y += s(14)
    y += s(50)
    bottom_top = y
    text_w = width - ((qr.width + s(40)) if qr is not None else 0)
    if cta:
        f = font(s(46), True)
        pill_w = min(text_w, round(d.textlength(cta, font=f)) + s(100))
        d.rounded_rectangle((0, y, pill_w, y + s(110)), radius=s(55), fill=rgb(brand))
        d.text((pill_w / 2, y + s(55)), cta, font=f, fill=rgb(on(brand)), anchor="mm")
        y += s(110) + s(30)
    for i, c in enumerate(contact):
        first = i == 0  # the web address (or phone) leads, in bold
        csize, rows = fit(d, c, text_w, (s(42), s(38), SMALLEST), 1, first)
        d.text((0, y), rows[0], font=font(csize, first), fill=INK if first else MUTED)
        y += round(csize * 1.4)
    if qr is not None:
        canvas.paste(qr, (width - qr.width, bottom_top))
        y = max(y, bottom_top + qr.width)
    return canvas.crop((0, 0, width, y))


def render(name: str, brand: str, headline: str, line: str, bullets: list[str], cta: str, contact: list[str],
           website: str, photo: Image.Image | None, paper: str) -> Image.Image:
    w_mm, h_mm = PAGES[paper]
    size = (round(w_mm * MM) + 2 * BLEED, round(h_mm * MM) + 2 * BLEED)
    k = size[0] / (round(148 * MM) + 2 * BLEED)  # A5 is the base; A4 scales up
    page = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(page)
    text = rgb(on(brand))
    if photo is not None:
        photo_h = round(size[1] * 0.36)
        page.paste(ImageOps.fit(photo, (size[0], photo_h), Image.LANCZOS, centering=(0.5, 0.45)), (0, 0))
        band = round(150 * k)
        d.rectangle((0, photo_h, size[0], photo_h + band), fill=rgb(brand))
        nsize, rows = fit(d, name, size[0] - 2 * (BLEED + MARGIN), (round(72 * k), round(60 * k), round(50 * k)),
                          1, True)
        d.text((BLEED + MARGIN, photo_h + band / 2), rows[0], font=font(nsize, True), fill=text, anchor="lm")
        top = photo_h + band
    else:
        top = round(size[1] * 0.2)
        d.rectangle((0, 0, size[0], top), fill=rgb(brand))
        nsize, rows = fit(d, name, size[0] - 2 * (BLEED + MARGIN), (round(120 * k), round(100 * k), round(84 * k)),
                          1, True)
        d.text((size[0] / 2, BLEED + (top - BLEED) / 2), rows[0], font=font(nsize, True), fill=text, anchor="mm")
    accent = rgb(brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA))
    width = size[0] - 2 * (BLEED + MARGIN)
    room = size[1] - BLEED - MARGIN - (top + MARGIN)
    scale = 1.6  # start big and shrink until it fits, so a short flyer fills the page
    while True:
        qr = qr_picture(website, round(300 * k * max(1.0, scale))) if website else None  # grows with the words
        block = body(width, k, accent, brand, headline, line, bullets, cta, contact, qr, scale)
        if block.height <= room:
            break
        scale -= 0.05
        if round(48 * k * scale) < SMALLEST:
            raise ValueError(f"That's too much writing for an {paper} flyer; shorten the bullets or the short line, "
                             "or use A4.")
    page.paste(block, (BLEED + MARGIN, top + MARGIN + (room - block.height) // 3))
    return page


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the flyer.")
    brand = colour(args.get("colour") or "")
    headline = clean(args.get("headline"))
    if not headline:
        raise ValueError("What's the flyer about? Give a headline, e.g. '20% off all cuts this November'.")
    if len(headline) > 80:
        raise ValueError("Keep the headline under 80 letters; put the rest in the short line or bullets.")
    bullets = [clean(b)[:90] for b in (args.get("bullets") or []) if clean(b)]
    if len(bullets) > MAX_BULLETS:
        raise ValueError(f"Use up to {MAX_BULLETS} bullet points; a flyer is read in seconds.")
    cta = clean(args.get("cta"))
    if len(cta) > 28:
        raise ValueError("Keep the button words short, e.g. 'Book online' (28 letters at most).")
    website = clean(args.get("website"))
    link = ""
    if website:
        link = website if "://" in website else "https://" + website
        if not re.match(r"(?i)^https://[^\s/]+\.[^\s/]+(/\S*)?$", link):
            raise ValueError(f"'{website}' isn't a web address; use something like lebosbakery.co.uk.")
    shown = re.sub(r"^https://(www\.)?", "", link).rstrip("/")
    contact = [x for x in (shown, clean(args.get("phone")), clean(args.get("address"))) if x]
    photo = None
    if args.get("photo"):
        if not args.get("folder"):
            raise ValueError("Say which memory folder the photo is in.")
        photo = load(memory.file_path(settings, str(args["folder"]), str(args["photo"])))
    paper = str(args.get("paper") or "A5").upper()
    if paper not in PAGES:
        raise ValueError("Pick A5 or A4 paper.")
    use_qr = args.get("qr", True) is not False and bool(link)
    page = render(name, brand, headline, clean(args.get("text"))[:200], bullets, cta, contact,
                  link if use_qr else "", photo, paper)
    slug = re.sub(r"[^a-z0-9]+", "-", str(args.get("title") or "flyer").lower()).strip("-")[:40] or "flyer"
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/print", create=True)
    page.save(path / f"{slug}.pdf", "PDF", resolution=DPI)
    page.save(path / f"{slug}.png", dpi=(DPI, DPI), optimize=True)
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made an {paper} flyer for {name} in {where}: {slug}.pdf to print (300 dpi, 3mm bleed) and {slug}.png "
            "to post online" + ("".join([f", with the photo {args['photo']}" if photo else "",
                                          (" and" if photo else ", with") + " a QR code to the website" if use_qr
                                          else ""])) + ". Nothing is smaller than 9pt.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_flyer",
        "description": "Make a one-sided A5 or A4 flyer in the brand colour: business name, big headline, short line, "
                       "up to 5 bullet points, a call-to-action button, website, phone and address, an optional QR "
                       "to the website and an optional photo from a memory folder. Never below 9pt. Saves a "
                       "print-ready PDF (3mm bleed) and PNG in Kinetic Web Designs/<name>/print. Answer in plain "
                       "words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (top of the flyer and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "headline": {"type": "string", "description": "e.g. '20% off all cuts this November'."},
                "text": {"type": "string", "description": "Short line under the headline."},
                "bullets": {"type": "array", "items": {"type": "string"}, "description": "Up to 5 points."},
                "cta": {"type": "string", "description": "Button words, e.g. 'Book online'."},
                "website": {"type": "string"},
                "phone": {"type": "string"},
                "address": {"type": "string", "description": "One line, e.g. '1 High St, Croydon CR0 1AA'."},
                "qr": {"type": "boolean", "description": "QR code to the website (default yes when there is one)."},
                "folder": {"type": "string", "description": "Memory folder with the photo (optional)."},
                "photo": {"type": "string", "description": "Photo in that folder (PNG/JPG/WebP)."},
                "paper": {"type": "string", "enum": ["A5", "A4"], "description": "Default A5."},
                "title": {"type": "string", "description": "File name, e.g. 'november offer' (default 'flyer')."},
            },
            "required": ["name", "colour", "headline"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
