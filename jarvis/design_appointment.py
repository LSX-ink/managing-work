"""Appointment cards: the small "your next appointment" card barbers, salons and clinics hand over at the till.

make_appointment_card draws a business-card-size (85 x 55mm) card at 300 dpi with 3mm bleed, words 4mm inside the
cut and never below 7pt, with the same specs as make_business_card and make_loyalty_card so they can go in one print
order. The front is the brand colour with the business name and a tagline; the back says "Your next appointment" and
has 1 to 3 write-in rows (day, date, time, and optionally who with), a short note such as "24 hours' notice to cancel,
please" and the phone number to call. Write-in lines are at least 6mm apart so handwriting fits. It saves
appointment.pdf (front and back), PNGs of each side and appointment-preview.png, in Kinetic Web Designs/<name>/print.
"""

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_cards import BLEED, DPI, INK, MM, MUTED, SAFE, SIZE, fit, front, preview
from design_contrast import AA, colour, fix, ratio, rgb
from design_extract import FOLDER
from docs_tools import font

NAMES = {"make_appointment_card"}
LINE = (190, 190, 198)
MIN_GAP = round(6 * MM)  # room to write by hand


def back(brand: str, rows: int, with_who: bool, note: str, phone: str) -> tuple[Image.Image, list[str]]:
    image = Image.new("RGB", SIZE, (255, 255, 255))
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, SIZE[0], BLEED + 14), fill=rgb(brand))
    accent = rgb(brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA))
    left, right = BLEED + SAFE, SIZE[0] - BLEED - SAFE
    width, cuts = right - left, []
    y = BLEED + SAFE + 24
    d.text((left, y), "Your next appointment" if rows == 1 else "Your next appointments", font=font(42, True),
           fill=accent)
    y += 66
    footer = [x for x in (note, f"To change it, call {phone}" if phone else "") if x]
    bottom = SIZE[1] - BLEED - SAFE - len(footer) * 40 - 30  # a clear gap above the note
    label = font(30)
    labels = ["Day", "Date", "Time"] + (["With"] if with_who else [])
    gap = (bottom - y) // rows
    if gap < MIN_GAP:
        raise ValueError("That's too many rows to write in by hand; use fewer rows or leave out the note.")
    for r in range(rows):
        base = y + round(gap * (r + 0.7))  # rows spread evenly, each line sitting low in its band
        cols = len(labels)
        col_w = width // cols
        for c, text in enumerate(labels):
            x = left + c * col_w
            d.text((x, base), text, font=label, fill=MUTED, anchor="ls")
            start = x + d.textlength(text, font=label) + 10
            d.line((start, base, x + col_w - 18, base), fill=LINE, width=3)
    y = bottom + 64
    for i, line in enumerate(footer):
        size, text, cut = fit(d, line, width, 30, i == 1)
        d.text((left, y), text, font=font(size, i == 1), fill=INK if i == 1 else MUTED, anchor="ls")
        y += 40
        cuts += ["the note" if i == 0 and note else "the phone line"] if cut else []
    return image, cuts


def run(settings: Settings, args: dict) -> str:
    clean = lambda k: " ".join(str(args.get(k) or "").split())  # noqa: E731
    business = clean("name")
    if not business:
        raise ValueError("Give the business name for the appointment card.")
    brand = colour(args.get("colour") or "")
    rows = int(args["rows"]) if args.get("rows") is not None else 2
    if not 1 <= rows <= 3:
        raise ValueError("Use 1 to 3 appointment rows (2 is usual).")
    note = clean("note")
    if note == "":
        note = "Please give 24 hours' notice to cancel."
    if note.lower() == "none":
        note = ""
    if len(note) > 70:
        raise ValueError("Keep the note short, e.g. 'Please give 24 hours' notice to cancel.' (70 letters at most).")
    phone = clean("phone")
    with_who = bool(args.get("with_who"))
    first, cut_front = front(brand, business, clean("tagline"))
    second, cut_back = back(brand, rows, with_who, note, phone)
    cuts = cut_front + cut_back
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(business, 'folder name')}/print", create=True)
    first.save(path / "appointment-front.png", dpi=(DPI, DPI))
    second.save(path / "appointment-back.png", dpi=(DPI, DPI))
    first.save(path / "appointment.pdf", "PDF", resolution=DPI, save_all=True, append_images=[second])
    preview([first, second]).save(path / "appointment-preview.png", optimize=True)
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made an appointment card for {business} in {where} with {rows} write-in row{'s' if rows > 1 else ''}"
            f"{' (day, date, time and who with)' if with_who else ' (day, date and time)'}: appointment.pdf (front "
            "and back) for the printer, appointment-front.png and appointment-back.png, and appointment-preview.png "
            "to show the client. It's 85 x 55mm with 3mm bleed, like their business and loyalty cards, so they can "
            "go in one order. Ask for matt or uncoated card so pens write on it."
            + (f" Heads up: {', '.join(cuts)} didn't fit at 7pt and {'was' if len(cuts) == 1 else 'were'} "
               "shortened." if cuts else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_appointment_card",
        "description": "Make a print-ready appointment card (85 x 55mm, 3mm bleed, 300 dpi, business-card size): "
                       "front in the brand colour with the business name, back with 'Your next appointment', 1-3 "
                       "write-in rows (day, date, time, optionally who with), a cancellation note and the phone "
                       "number. Saves appointment.pdf, PNGs and a preview in Kinetic Web Designs/<name>/print. Use "
                       "for barbers, salons, clinics and tutors. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (front and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "tagline": {"type": "string", "description": "Short line under the name on the front."},
                "rows": {"type": "integer", "minimum": 1, "maximum": 3, "description": "Write-in rows (default 2)."},
                "with_who": {"type": "boolean", "description": "Add a 'With' box for the stylist or barber."},
                "note": {"type": "string", "description": "Small note (default 24 hours' notice); 'none' for none."},
                "phone": {"type": "string", "description": "Number to call to change it."},
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
