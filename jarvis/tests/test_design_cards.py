import asyncio

import pytest
from PIL import Image

import design_cards as dc
import tools
from config import Settings

FULL = {"name": "Lebo's Bakery", "colour": "#c2410c", "tagline": "Fresh bread every morning", "person": "Lebo Mokoena",
        "role": "Head baker", "phone": "07700 900123", "email": "hello@lebosbakery.co.uk",
        "website": "lebosbakery.co.uk", "address": "1 High St, Croydon CR0 1AA"}


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dc.run_tool("make_business_card", args, settings))


def test_print_ready_card(s, tmp_path):
    out = ask(FULL, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "print"
    assert "QR code to the website" in out and "Heads up" not in out
    assert dc.TRIM == (1004, 650) and dc.SIZE == (1074, 720)
    front, back = Image.open(folder / "card-front.png"), Image.open(folder / "card-back.png")
    assert front.size == back.size == dc.SIZE
    assert round(front.info["dpi"][0]) == 300
    assert front.getpixel((2, 2)) == (0xc2, 0x41, 0x0c)  # brand colour runs into the bleed
    assert back.getpixel((2, 2)) == (0xc2, 0x41, 0x0c) and back.getpixel((dc.SIZE[0] // 2, 300)) == (255, 255, 255)
    assert b"/Count 2" in (folder / "card.pdf").read_bytes()  # front and back
    assert Image.open(folder / "card-preview.png").width > 2 * dc.TRIM[0]


def test_words_stay_inside_safe_zone(s, tmp_path):
    ask(FULL, s)
    for side in ("card-front.png", "card-back.png"):
        image = Image.open(tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "print" / side).convert("RGB")
        background = image.getpixel((dc.SIZE[0] // 2, dc.SIZE[1] - 3))
        inner = dc.BLEED + dc.SAFE
        for x in range(dc.SIZE[0]):
            for y in list(range(dc.BLEED + 20, inner)) + list(range(dc.SIZE[1] - inner, dc.SIZE[1])):
                assert image.getpixel((x, y)) == background, (side, x, y)
        for y in range(dc.BLEED + 20, dc.SIZE[1]):
            for x in list(range(inner)) + list(range(dc.SIZE[0] - inner, dc.SIZE[0])):
                assert image.getpixel((x, y)) == background, (side, x, y)


def test_contact_qr_and_fallback():
    card = dc.vcard("Lebo's Bakery", "Lebo", "Baker", "0770", "a@b.co", "lebos.co.uk")
    assert card.startswith("BEGIN:VCARD") and "TEL:0770" in card and card.endswith("END:VCARD")
    qr = dc.qr_picture(card, 260)
    assert qr.width <= 260 and qr.getpixel((0, 0)) == (255, 255, 255)


def test_long_text_and_contact_fallback(s):
    out = ask(dict(FULL, qr="contact", name="X" * 50, role="r" * 400), s)
    assert "shortened" in out and "the business name" in out and "the job title" in out
    assert "too long for a QR code, so it opens the website" in out


def test_bad_input(s):
    assert "business name" in ask({"colour": "#000"}, s)
    assert "at least one way to reach them" in ask({"name": "A", "colour": "#000"}, s)
    assert "website, contact or none" in ask({"name": "A", "colour": "#000", "phone": "1", "qr": "map"}, s)
    assert "Add the website" in ask({"name": "A", "colour": "#000", "phone": "1", "qr": "website"}, s)
    assert "no QR code" in ask({"name": "A", "colour": "#000", "phone": "1"}, s)
    assert "Can't read the colour" in ask({"name": "A", "colour": "nope", "phone": "1"}, s)


def test_registered():
    assert dc in tools.ABILITIES
