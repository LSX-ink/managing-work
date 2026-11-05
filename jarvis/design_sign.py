"""QR signs: an A4 or A5 "scan me" sign for a counter, table or window, in the brand colour.

make_qr_sign draws a portrait sign with the business name in a brand-colour header, a big headline such as "Scan to
leave us a review", a large QR code, a short line and the link written out underneath for anyone who can't scan. The
QR goes to a web page (a booking page, menu or Google review link), a phone number to call, or the shop's Wi-Fi so
guests join without typing the password. The QR is drawn big enough to scan from about a metre away on A5 and further
on A4, with the quiet border scanners need. Pages are 300 dpi with 3mm bleed. It saves <slug>.pdf for printing and
<slug>.png, in Kinetic Web Designs/<name>/print.
"""

import re

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_cards import qr_picture
from design_contrast import AA, colour, fix, ratio, rgb
from design_extract import FOLDER
from design_palette import on
from design_social import fit
from docs_tools import font

NAMES = {"make_qr_sign"}
DPI = 300
MM = DPI / 25.4
PAGES = {"A4": (210, 297), "A5": (148, 210)}
BLEED, MARGIN = round(3 * MM), round(14 * MM)
INK, MUTED = (24, 24, 27), (82, 82, 91)
HEADLINES = {"link": "Scan me", "phone": "Scan to call us", "wifi": "Scan to join our Wi-Fi"}
SECURITY = {"wpa": "WPA", "wep": "WEP", "none": "nopass"}


def wifi_text(network: str, password: str, security: str) -> str:
    """The standard WIFI: text phones read from a QR; \\ ; , : and " are escaped as the format asks."""
    esc = lambda s: re.sub(r'([\\;,:"])', r"\\\1", s)  # noqa: E731
    kind = SECURITY.get(security.lower())
    if kind is None:
        raise ValueError("For Wi-Fi security pick wpa (most routers), wep or none.")
    if not network:
        raise ValueError("Give the Wi-Fi network name.")
    if kind != "nopass" and not password:
        raise ValueError("Give the Wi-Fi password, or pick security 'none' for an open network.")
    return f"WIFI:T:{kind};S:{esc(network)};" + (f"P:{esc(password)};" if kind != "nopass" else "") + ";"


def target(args: dict) -> tuple[str, str, str]:
    """(kind, what the QR holds, what is written under it)."""
    clean = lambda k: " ".join(str(args.get(k) or "").split())  # noqa: E731
    kind = clean("kind").lower() or ("wifi" if args.get("wifi_name") else "phone" if args.get("phone") and
                                     not args.get("link") else "link")
    if kind == "link":
        link = clean("link")
        if not link:
            raise ValueError("Give the link the QR should open, e.g. the Google review link or booking page.")
        full = link if "://" in link else "https://" + link
        if not re.match(r"(?i)^https://[^\s/]+\.[^\s/]+(/\S*)?$", full):
            raise ValueError(f"'{link}' isn't a web address; use something like lebosbakery.co.uk/book.")
        return kind, full, re.sub(r"^https://(www\.)?", "", full).rstrip("/")
    if kind == "phone":
        phone = clean("phone")
        digits = re.sub(r"[^\d+]", "", phone)
        if len(re.sub(r"\D", "", digits)) < 6:
            raise ValueError("Give the phone number to call.")
        return kind, "tel:" + digits, phone
    if kind == "wifi":
        network, password = str(args.get("wifi_name") or "").strip(), str(args.get("wifi_password") or "")
        security = str(args.get("wifi_security") or "wpa")
        text = wifi_text(network, password, security)
        shown = f"Network: {network}" + (f" · Password: {password}" if password and security.lower() != "none" else "")
        return kind, text, shown
    raise ValueError("Pick what the QR does: link, phone or wifi.")


def render(name: str, brand: str, headline: str, line: str, qr_text: str, shown: str, paper: str) -> Image.Image:
    w_mm, h_mm = PAGES[paper]
    size = (round(w_mm * MM) + 2 * BLEED, round(h_mm * MM) + 2 * BLEED)
    k = 1.0 if paper == "A4" else 0.72
    image = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(image)
    header = round(360 * k) + BLEED
    d.rectangle((0, 0, size[0], header), fill=rgb(brand))
    inner = size[0] - 2 * (BLEED + MARGIN)
    big, rows = fit(d, name, inner, tuple(round(s * k) for s in (130, 110, 90, 76)), 1, True)
    d.text((size[0] / 2, BLEED + (header - BLEED) / 2), rows[0], font=font(big, True), fill=rgb(on(brand)),
           anchor="mm")
    accent = rgb(brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA))
    body = Image.new("RGB", (size[0], size[1] * 2), (255, 255, 255))  # drawn here, then centred under the header
    b = ImageDraw.Draw(body)
    y = 0
    hsize, hrows = fit(b, headline, inner, tuple(round(s * k) for s in (170, 150, 130, 110, 96)), 2, True)
    for row in hrows:
        b.text((size[0] / 2, y), row, font=font(hsize, True), fill=INK, anchor="mt")
        y += round(hsize * 1.12)
    qr = qr_picture(qr_text, 1500 if paper == "A4" else 1000)  # about 127mm on A4, 85mm on A5 (scans from 1m+)
    side = qr.width  # whole pixels per square keeps every square the same size, so it scans cleanly
    y += round(90 * k)
    body.paste(qr, ((size[0] - side) // 2, y))  # its white quiet border sits inside the frame
    b.rounded_rectangle(((size[0] - side) / 2, y, (size[0] + side) / 2, y + side), radius=round(48 * k),
                        outline=accent, width=max(6, round(10 * k)))
    y += side + round(80 * k)
    if line:
        lsize, lrows = fit(b, line, inner, tuple(round(s * k) for s in (72, 64, 56, 48)), 2, False)
        for row in lrows:
            b.text((size[0] / 2, y), row, font=font(lsize), fill=MUTED, anchor="mt")
            y += round(lsize * 1.3)
        y += round(30 * k)
    ssize, srows = fit(b, shown, inner, tuple(round(s * k) for s in (64, 56, 48, 40)), 2, True)
    for row in srows:
        b.text((size[0] / 2, y), row, font=font(ssize, True), fill=accent, anchor="mt")
        y += round(ssize * 1.25)
    room = size[1] - BLEED - MARGIN - header - MARGIN
    if y > room:
        raise ValueError("That's too much writing for the sign; shorten the headline or the short line.")
    image.paste(body.crop((0, 0, size[0], y)), (0, header + MARGIN + (room - y) // 2))
    return image


def run(settings: Settings, args: dict) -> str:
    name = " ".join(str(args.get("name") or "").split())
    if not name:
        raise ValueError("Give the business name for the sign.")
    brand = colour(args.get("colour") or "")
    kind, qr_text, shown = target(args)
    headline = " ".join(str(args.get("headline") or "").split()) or HEADLINES[kind]
    if len(headline) > 60:
        raise ValueError("Keep the headline short, e.g. 'Scan to leave us a review' (60 letters at most).")
    line = " ".join(str(args.get("text") or "").split())[:120]
    paper = str(args.get("paper") or "A5").upper()
    if paper not in PAGES:
        raise ValueError("Pick A4 or A5 paper.")
    page = render(name, brand, headline, line, qr_text, shown, paper)
    slug = re.sub(r"[^a-z0-9]+", "-", str(args.get("title") or f"{kind} sign").lower()).strip("-")[:40] or "sign"
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/print", create=True)
    page.save(path / f"{slug}.pdf", "PDF", resolution=DPI)
    page.save(path / f"{slug}.png", dpi=(DPI, DPI), optimize=True)
    where = path.relative_to(memory.root(settings)).as_posix()
    does = {"link": f"opens {shown}", "phone": f"calls {shown}", "wifi": "joins the Wi-Fi"}[kind]
    return (f"Made an {paper} QR sign for {name} in {where}: {slug}.pdf to print (300 dpi, 3mm bleed) and {slug}.png. "
            f"Scanning it {does}. Test it with a phone camera before printing a batch."
            + (" The Wi-Fi password is printed on the sign, so only use it for a guest network." if kind == "wifi"
               else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_qr_sign",
        "description": "Make an A4 or A5 'scan me' sign for a counter, table or window in the brand colour: business "
                       "name header, big headline, a large QR code and the link written under it. The QR can open a "
                       "link (Google reviews, booking page, menu), call a phone number, or join the Wi-Fi. Saves a "
                       "print-ready PDF (3mm bleed) and PNG in Kinetic Web Designs/<name>/print. Answer in plain "
                       "words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (header and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "kind": {"type": "string", "enum": ["link", "phone", "wifi"], "description": "What the QR does."},
                "link": {"type": "string", "description": "Web address for kind link, e.g. a Google review link."},
                "phone": {"type": "string", "description": "Number for kind phone."},
                "wifi_name": {"type": "string", "description": "Network name for kind wifi."},
                "wifi_password": {"type": "string"},
                "wifi_security": {"type": "string", "enum": ["wpa", "wep", "none"], "description": "Default wpa."},
                "headline": {"type": "string", "description": "e.g. 'Scan to leave us a review' (60 letters max)."},
                "text": {"type": "string", "description": "Short line under the QR, e.g. 'It takes 30 seconds'."},
                "paper": {"type": "string", "enum": ["A4", "A5"], "description": "Default A5."},
                "title": {"type": "string", "description": "File name, e.g. 'review sign'."},
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
