"""Gift vouchers ready for the printer: DL-size vouchers in the brand colour, each with its own code to check off.

make_gift_voucher draws 210 x 99mm vouchers (the DL size that fits a standard gift envelope) at 300 dpi with 3mm of
bleed, keeping words 4mm inside the cut line and never smaller than 7pt. The left panel is the brand colour with the
business name and "Gift voucher"; the right side has what it's worth (an amount like "£25" or a treat like "One free
haircut"), who it's for, a unique code, the expiry date, a short terms line and an optional QR code to the website.
Codes use letters and numbers that can't be mixed up (no 0/O or 1/I), made with Python's secrets module so they can't
be guessed. It saves one PDF with a page per voucher, a preview PNG of the first one and a CSV list of the codes (with
a "used" column for the owner to tick off), in Kinetic Web Designs/<name>/print. Earlier batches are never overwritten.
"""

import csv
import datetime as dt
import re
import secrets

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_cards import fit, qr_picture
from design_contrast import AA, colour, fix, ratio, rgb
from design_extract import FOLDER
from design_palette import on
from docs_tools import font

NAMES = {"make_gift_voucher"}
DPI = 300
MM = DPI / 25.4
TRIM = (round(210 * MM), round(99 * MM))  # 2480 x 1169
BLEED, SAFE = round(3 * MM), round(4 * MM)
SIZE = (TRIM[0] + 2 * BLEED, TRIM[1] + 2 * BLEED)
PANEL = round(TRIM[0] * 0.36) + BLEED  # brand panel width, from the left edge of the bleed
INK, MUTED = (24, 24, 27), (82, 82, 91)
LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I to misread
MAX_COUNT = 50


def code(prefix: str) -> str:
    part = lambda: "".join(secrets.choice(LETTERS) for _ in range(4))  # noqa: E731
    return f"{prefix}-{part()}-{part()}" if prefix else f"{part()}-{part()}"


def codes(prefix: str, count: int) -> list[str]:
    out: list[str] = []
    while len(out) < count:
        c = code(prefix)
        if c not in out:
            out.append(c)
    return out


def expiry(args: dict, today: dt.date) -> dt.date:
    given = str(args.get("expires") or "").strip()
    if given:
        try:
            day = dt.date.fromisoformat(given)
        except ValueError:
            raise ValueError("Give the expiry date like 2027-11-04.") from None
        if day <= today:
            raise ValueError("The expiry date has to be after today.")
        return day
    months = int(args.get("months") or 12)
    if not 1 <= months <= 60:
        raise ValueError("Make vouchers last between 1 and 60 months (12 is usual; UK gift cards often last 2 years).")
    year, month = divmod(today.month - 1 + months, 12)
    year, month = today.year + year, month + 1
    last = (dt.date(year + month // 12, month % 12 + 1, 1) - dt.timedelta(days=1)).day
    return dt.date(year, month, min(today.day, last))


def nice(day: dt.date) -> str:
    return f"{day.day} {day:%b %Y}"


def draw(brand: str, business: str, value: str, to: str, voucher_code: str, until: dt.date, terms: str,
         qr: Image.Image | None) -> tuple[Image.Image, list[str]]:
    image = Image.new("RGB", SIZE, (255, 255, 255))
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, PANEL, SIZE[1]), fill=rgb(brand))  # into the bleed on three sides
    text, cuts = rgb(on(brand)), []
    left_w = PANEL - BLEED - 2 * SAFE - 80  # 40px in from the safe line on both sides
    size, name, cut = fit(d, business, left_w, 110, True)
    cuts += ["the business name"] if cut else []
    mid = SIZE[1] / 2
    d.text((BLEED + SAFE + 40, mid - 20), name, font=font(size, True), fill=text, anchor="ls")
    d.text((BLEED + SAFE + 40, mid + 30), "GIFT VOUCHER", font=font(54, True), fill=text, anchor="lt")
    accent = rgb(brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA))
    x = PANEL + SAFE + 60
    right = SIZE[0] - BLEED - SAFE - 20
    if qr is not None:
        side = min(qr.width, 330)
        qr = qr.resize((side, side), Image.NEAREST)
        image.paste(qr, (right - side, SIZE[1] - BLEED - SAFE - 20 - side))
    width = right - x
    y = BLEED + SAFE + 70
    if to:
        small, line, cut = fit(d, f"For {to}", width, 56, False)
        d.text((x, y), line, font=font(small), fill=MUTED)
        cuts += ["the name it's for"] if cut else []
    y += 90
    size, line, cut = fit(d, value, width, 230, True)
    d.text((x, y), line, font=font(size, True), fill=accent)
    cuts += ["what it's worth"] if cut else []
    y += round(size * 1.2) + 30
    text_w = width - ((qr.width + 40) if qr is not None else 0)
    d.text((x, y), "CODE", font=font(36, True), fill=MUTED)
    d.text((x, y + 50), voucher_code, font=font(72, True), fill=INK)
    d.text((x, y + 170), f"Valid until {nice(until)}", font=font(44), fill=INK)
    if terms:
        small, line, cut = fit(d, terms, text_w, 36, False)
        d.text((x, SIZE[1] - BLEED - SAFE - 40), line, font=font(small), fill=MUTED, anchor="ls")
        cuts += ["the terms"] if cut else []
    return image, cuts


def free_name(path, stem: str) -> str:
    name, n = stem, 2
    while (path / f"{name}.pdf").exists() or (path / f"{name}.csv").exists():
        name, n = f"{stem}-{n}", n + 1
    return name


def run(settings: Settings, args: dict, today: dt.date | None = None) -> str:
    clean = lambda k: " ".join(str(args.get(k) or "").split())  # noqa: E731
    business = clean("name")
    if not business:
        raise ValueError("Give the business name for the voucher.")
    brand = colour(args.get("colour") or "")
    value = clean("value")
    if not value:
        raise ValueError("Say what the voucher is worth, e.g. '£25' or 'One free haircut'.")
    if len(value) > 40:
        raise ValueError("Keep what it's worth short, e.g. '£25' or 'One free haircut' (40 letters at most).")
    count = int(args.get("count") or 1)
    if not 1 <= count <= MAX_COUNT:
        raise ValueError(f"Make between 1 and {MAX_COUNT} vouchers at a time.")
    prefix = re.sub(r"[^A-Z0-9]", "", clean("prefix").upper())[:6]
    today = today or dt.date.today()
    until = expiry(args, today)
    terms = clean("terms") or "One use only. Not exchangeable for cash."
    website = clean("website")
    qr = None
    if website:
        link = website if "://" in website else "https://" + website
        if not re.match(r"(?i)^https://[^\s/]+\.[^\s/]+", link):
            raise ValueError(f"'{website}' isn't a web address; use something like lebosbakery.co.uk.")
        qr = qr_picture(link, 330)
    to = clean("to")
    made = codes(prefix, count)
    pages, cuts = [], []
    for c in made:
        page, cut = draw(brand, business, value, to, c, until, terms, qr)
        pages.append(page)
        cuts += [x for x in cut if x not in cuts]
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(business, 'folder name')}/print", create=True)
    stem = free_name(path, f"vouchers-{today.isoformat()}")
    pages[0].save(path / f"{stem}.pdf", "PDF", resolution=DPI, save_all=True, append_images=pages[1:])
    pages[0].crop((BLEED, BLEED, BLEED + TRIM[0], BLEED + TRIM[1])).resize(
        (TRIM[0] // 2, TRIM[1] // 2), Image.LANCZOS).save(path / f"{stem}-preview.png", optimize=True)
    with open(path / f"{stem}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "value", "for", "valid until", "used"])
        w.writerows([c, value, to, until.isoformat(), ""] for c in made)
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made {count} gift voucher{'s' if count != 1 else ''} for {business} worth {value}, valid until "
            f"{nice(until)}, in {where}: {stem}.pdf to print (DL 210 x 99mm, 3mm bleed, 300 dpi, one voucher per "
            f"page), {stem}-preview.png to show the client, and {stem}.csv listing every code with a 'used' column "
            "to tick off when one is spent." + (" Each voucher has a QR code to the website." if qr else "")
            + (f" Heads up: {', '.join(cuts)} didn't fit at 7pt and {'was' if len(cuts) == 1 else 'were'} shortened."
               if cuts else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_gift_voucher",
        "description": "Make print-ready gift vouchers (DL 210 x 99mm, 3mm bleed, 300 dpi) in the brand colour: what "
                       "it's worth, who it's for, a unique hard-to-guess code each, expiry date, terms and an "
                       "optional QR to the website. Makes 1-50 at once as one PDF (a page each), a preview PNG and "
                       "a CSV of codes to tick off, in Kinetic Web Designs/<name>/print. Use for salons, barbers, "
                       "cafés and stays. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (on the voucher and the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "value": {"type": "string", "description": "e.g. '£25' or 'One free haircut'."},
                "count": {"type": "integer", "minimum": 1, "maximum": 50, "description": "How many (default 1)."},
                "to": {"type": "string", "description": "Who it's for (optional; blank vouchers sell better)."},
                "expires": {"type": "string", "description": "Expiry date like 2027-11-04 (optional)."},
                "months": {"type": "integer", "description": "Or how many months it lasts (default 12)."},
                "terms": {"type": "string", "description": "Short terms line (default: one use, no cash)."},
                "website": {"type": "string", "description": "For the QR code, e.g. lebosbakery.co.uk."},
                "prefix": {"type": "string", "description": "Up to 6 letters at the start of each code, e.g. 'LEBO'."},
            },
            "required": ["name", "colour", "value"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
