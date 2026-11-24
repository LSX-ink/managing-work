import asyncio

import pytest
from PIL import Image

import design_flyer as df
import memory
import tools
from config import Settings

OFFER = {"name": "Fade Inn", "colour": "#b91c1c", "headline": "20% off all cuts this November",
         "text": "Every weekday before 3pm.", "bullets": ["Skin fades and beard trims", "Walk-ins welcome"],
         "cta": "Book online", "website": "fadeinn.co.uk", "phone": "0121 496 0000",
         "address": "21 High St, Birmingham B1 1AA"}


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(df.run_tool("make_flyer", args, settings))


def size_of(paper):
    w, h = df.PAGES[paper]
    return round(w * df.MM) + 2 * df.BLEED, round(h * df.MM) + 2 * df.BLEED


def test_a5_flyer(s, tmp_path):
    out = ask({**OFFER, "title": "November offer"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Fade Inn" / "print"
    assert "Made an A5 flyer" in out and "with a QR code" in out and "9pt" in out
    page = Image.open(folder / "november-offer.png")
    assert page.size == size_of("A5") and round(page.info["dpi"][0]) == 300
    assert page.getpixel((3, 3)) == (0xb9, 0x1c, 0x1c)  # brand block runs into the bleed
    assert (folder / "november-offer.pdf").read_bytes().startswith(b"%PDF")


def test_photo_on_top(s, tmp_path):
    folder = memory.folder(s, "Work", create=True)
    Image.new("RGB", (1200, 800), (10, 200, 30)).save(folder / "shop.png")
    out = ask({**OFFER, "folder": "Work", "photo": "shop.png", "paper": "A4", "qr": False}, s)
    assert "Made an A4 flyer" in out and "with the photo shop.png" in out and "QR" not in out
    page = Image.open(tmp_path / "Kinetic Web Designs" / "Fade Inn" / "print" / "flyer.png")
    assert page.size == size_of("A4") and page.getpixel((page.width // 2, 50)) == (10, 200, 30)


def test_short_flyer_uses_bigger_type(s):
    short = df.render("X", "#2563eb", "Open Sundays", "", [], "", ["x.co.uk"], "", None, "A5")
    long = df.render("X", "#2563eb", "Open Sundays", "A longer line " * 8, ["Point " * 10] * 5, "Book now",
                     ["x.co.uk", "0121 496 0000", "1 High St"], "https://x.co.uk", None, "A5")

    def first_ink_row(img):
        top = round(img.height * 0.2) + df.MARGIN
        for y in range(top, img.height):
            if any(img.getpixel((x, y))[0] < 100 for x in range(df.BLEED + df.MARGIN, img.width // 2, 4)):
                return y
        return img.height

    def headline_height(img):
        y0 = first_ink_row(img)
        y = y0
        while any(img.getpixel((x, y))[0] < 100 for x in range(df.BLEED + df.MARGIN, img.width // 2, 4)):
            y += 1
        return y - y0

    assert headline_height(short) > headline_height(long)


def test_too_much_writing():
    with pytest.raises(ValueError, match="too much writing"):
        df.render("X", "#2563eb", "A " * 39, "Long " * 40, ["word " * 80] * 5, "Book now",
                  ["x.co.uk", "0121 496 0000", "1 High St"], "https://x.co.uk", None, "A5")


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000", "headline": "Hi"}, "business name"),
    ({"name": "X", "colour": "#000"}, "headline"),
    ({"name": "X", "colour": "#000", "headline": "x" * 81}, "80 letters"),
    ({"name": "X", "colour": "#000", "headline": "Hi", "bullets": ["a"] * 6}, "up to 5"),
    ({"name": "X", "colour": "#000", "headline": "Hi", "cta": "x" * 29}, "28 letters"),
    ({"name": "X", "colour": "#000", "headline": "Hi", "website": "javascript:alert(1)"}, "isn't a web address"),
    ({"name": "X", "colour": "#000", "headline": "Hi", "photo": "a.png"}, "which memory folder"),
    ({"name": "X", "colour": "#000", "headline": "Hi", "paper": "A3"}, "A5 or A4"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert df in tools.ABILITIES and [t["name"] for t in df.tool_definitions()] == ["make_flyer"]
