"""Business cards ready for the printer: front and back at the standard UK/EU size, with bleed, in the brand colour.

make_business_card draws an 85 x 55mm card at 300 dpi with 3mm of bleed on every side (what online printers such as
Moo or Vistaprint ask for), keeping all words 4mm inside the cut line. The front is the brand colour with the
business name and an optional tagline; the back has the person's name and job, phone, email, web address and address,
and a QR code (the website, or a contact card that saves straight into a phone) drawn with artstudio_qr. Text colours
are picked for contrast and nothing is printed smaller than 7pt. It saves card-front.png, card-back.png, a two-page
card.pdf to upload to the printer, and card-preview.png to show a client, in Kinetic Web Designs/<name>/print.
"""

from PIL import Image, ImageDraw, ImageFilter

import artstudio_qr
import memory
from config import Settings
from design_contrast import colour, rgb
from design_extract import FOLDER
from design_palette import on
from docs_tools import font

NAMES = {"make_business_card"}
DPI = 300
MM = DPI / 25.4
TRIM = (round(85 * MM), round(55 * MM))  # 1004 x 650
BLEED = round(3 * MM)  # 35
SAFE = round(4 * MM)  # words stay this far inside the cut line
SIZE = (TRIM[0] + 2 * BLEED, TRIM[1] + 2 * BLEED)
SMALLEST = round(7 / 72 * DPI)  # 7pt is the smallest print most people can read (29px)
INK, MUTED = (24, 24, 27), (82, 82, 91)


def fit(draw: ImageDraw.ImageDraw, text: str, width: int, start: int, bold: bool) -> tuple[int, str, bool]:
    """(size, text, cut): the biggest size from `start` down to 7pt that fits; past that the text is cut with '...'."""
    for size in range(start, SMALLEST - 1, -2):
        if draw.textlength(text, font=font(size, bold)) <= width:
            return size, text, False
    f, cut = font(SMALLEST, bold), text
    while cut and draw.textlength(cut + "...", font=f) > width:
        cut = cut[:-1].rstrip()
    return SMALLEST, cut + "...", True


def vcard(business: str, person: str, role: str, phone: str, email: str, website: str) -> str:
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{person or business}", f"ORG:{business}"]
    lines += [f"TITLE:{role}"] if role else []
    lines += [f"TEL:{phone}"] if phone else []
    lines += [f"EMAIL:{email}"] if email else []
    lines += [f"URL:{website}"] if website else []
    return "\n".join(lines + ["END:VCARD"])


def qr_picture(text: str, size: int) -> Image.Image:
    matrix = artstudio_qr.encode(text)
    modules = len(matrix) + 8  # 4 modules of quiet space on each side, which scanners need
    return artstudio_qr.image(matrix, scale=max(1, size // modules), border=4)


def front(brand: str, business: str, tagline: str) -> tuple[Image.Image, list[str]]:
    image = Image.new("RGB", SIZE, rgb(brand))
    d = ImageDraw.Draw(image)
    text, cuts = rgb(on(brand)), []
    width = TRIM[0] - 2 * SAFE
    size, name, cut = fit(d, business, width, 96, True)
    cuts += ["the business name"] if cut else []
    middle = SIZE[1] / 2
    if tagline:
        small, line, cut = fit(d, tagline, width, 40, False)
        cuts += ["the tagline"] if cut else []
        d.text((SIZE[0] / 2, middle - 10), name, font=font(size, True), fill=text, anchor="ms")
        d.text((SIZE[0] / 2, middle + 24), line, font=font(small), fill=text, anchor="mt")
    else:
        d.text((SIZE[0] / 2, middle), name, font=font(size, True), fill=text, anchor="mm")
    return image, cuts


def back(brand: str, person: str, role: str, lines: list[str], qr: Image.Image | None) -> tuple[Image.Image, list]:
    image = Image.new("RGB", SIZE, (255, 255, 255))
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, SIZE[0], BLEED + 14), fill=rgb(brand))  # a brand stripe along the top, into the bleed
    left, top = BLEED + SAFE, BLEED + SAFE + 20
    right = SIZE[0] - BLEED - SAFE
    if qr is not None:
        side = min(qr.width, TRIM[1] - 2 * SAFE - 40)
        qr = qr.resize((side, side), Image.NEAREST)
        image.paste(qr, (right - side, SIZE[1] - BLEED - SAFE - side))
        right -= side + 24
    width, y, cuts = right - left, top, []
    if person:
        size, text, cut = fit(d, person, width, 52, True)
        d.text((left, y), text, font=font(size, True), fill=INK)
        y += round(size * 1.2)
        cuts += ["the name"] if cut else []
    if role:
        size, text, cut = fit(d, role, width, 34, False)
        d.text((left, y), text, font=font(size), fill=MUTED)
        y += round(size * 1.3)
        cuts += ["the job title"] if cut else []
    y = max(y + 24, SIZE[1] - BLEED - SAFE - len(lines) * 44)  # contact lines sit at the bottom
    for line in lines:
        size, text, cut = fit(d, line, width, 32, False)
        d.text((left, y), text, font=font(size), fill=INK)
        y += 44
        cuts += [f"'{line}'"] if cut else []
    return image, cuts


def preview(sides: list[Image.Image]) -> Image.Image:
    """Both sides trimmed to the cut line, side by side on a soft grey, as a client would hold them."""
    gap, pad = 60, 80
    canvas = Image.new("RGBA", (pad * 2 + TRIM[0] * 2 + gap, pad * 2 + TRIM[1]), (236, 236, 240, 255))
    for i, side in enumerate(sides):
        card = side.crop((BLEED, BLEED, BLEED + TRIM[0], BLEED + TRIM[1]))
        mask = Image.new("L", TRIM, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, TRIM[0] - 1, TRIM[1] - 1), radius=18, fill=255)
        x = pad + i * (TRIM[0] + gap)
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((x, pad + 12, x + TRIM[0], pad + TRIM[1] + 12), radius=18,
                                                 fill=(0, 0, 0, 60))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(16)))
        canvas.paste(card, (x, pad), mask)
    return canvas.convert("RGB")


def clean(args: dict, key: str) -> str:
    return " ".join(str(args.get(key) or "").split())


def run(settings: Settings, args: dict) -> str:
    business = clean(args, "name")
    if not business:
        raise ValueError("Give the business name for the card.")
    brand = colour(args.get("colour") or "")
    person, role, tagline = clean(args, "person"), clean(args, "role"), clean(args, "tagline")
    phone, email, website, address = (clean(args, k) for k in ("phone", "email", "website", "address"))
    lines = [x for x in (phone, email, website, address) if x]
    if not lines:
        raise ValueError("Add at least one way to reach them: phone, email, website or address.")
    want = str(args.get("qr") or ("website" if website else "none")).lower()
    if want not in ("website", "contact", "none"):
        raise ValueError("For the QR code pick website, contact or none.")
    notes, qr, used = [], None, want
    if want == "website" and not website:
        raise ValueError("Add the website for the QR code, or pick qr 'contact' or 'none'.")
    if want != "none":
        text = website if want == "website" else vcard(business, person, role, phone, email, website)
        if want == "website" and "://" not in text:
            text = "https://" + text
        try:
            qr = qr_picture(text, 260)
        except ValueError:
            if not website:
                raise ValueError("The contact details are too long for a QR code; use qr 'website' or 'none'.") \
                    from None
            qr = qr_picture(website if "://" in website else "https://" + website, 260)
            used = "website"
            notes.append("the contact details were too long for a QR code, so it opens the website instead")
    first, cut_front = front(brand, business, tagline)
    second, cut_back = back(brand, person, role, lines, qr)
    cuts = cut_front + cut_back
    if cuts:
        notes.append(f"{', '.join(cuts)} didn't fit at 7pt and {'was' if len(cuts) == 1 else 'were'} shortened")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(business, 'folder name')}/print", create=True)
    first.save(path / "card-front.png", dpi=(DPI, DPI))
    second.save(path / "card-back.png", dpi=(DPI, DPI))
    first.save(path / "card.pdf", "PDF", resolution=DPI, save_all=True, append_images=[second])
    preview([first, second]).save(path / "card-preview.png", optimize=True)
    where = path.relative_to(memory.root(settings)).as_posix()
    qr_words = {"website": "a QR code to the website", "contact": "a QR code that saves the contact to a phone",
                "none": "no QR code"}[used]
    return (f"Made a business card for {business} in {where}: card.pdf (front and back) to upload to a printer such "
            f"as Moo or Vistaprint, card-front.png and card-back.png, and card-preview.png to show the client. "
            f"It's 85 x 55mm with 3mm bleed at 300 dpi, words kept 4mm inside the cut, with {qr_words}."
            + (" Heads up: " + "; ".join(notes) + "." if notes else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_business_card",
        "description": "Make a print-ready business card (85 x 55mm, 3mm bleed, 300 dpi): front in the brand colour "
                       "with the business name and tagline, back with the person's name, job, phone, email, website, "
                       "address and a QR code (website or a phone contact card). Saves card.pdf for the printer, "
                       "front and back PNGs and a preview in Kinetic Web Designs/<name>/print. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (on the front and the folder name)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "tagline": {"type": "string", "description": "Short line under the name on the front."},
                "person": {"type": "string", "description": "The card holder's name."},
                "role": {"type": "string", "description": "Their job, e.g. 'Head baker'."},
                "phone": {"type": "string"},
                "email": {"type": "string"},
                "website": {"type": "string", "description": "e.g. lebosbakery.co.uk"},
                "address": {"type": "string", "description": "One short line, e.g. '1 High St, Croydon CR0 1AA'."},
                "qr": {"type": "string", "enum": ["website", "contact", "none"],
                       "description": "What the QR code does (default website when there is one)."},
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
