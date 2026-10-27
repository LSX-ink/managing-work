import asyncio

import pytest
from PIL import Image, ImageDraw

import design_mockup as dm
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


@pytest.fixture
def folder(tmp_path):
    path = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery"
    path.mkdir(parents=True)
    page = Image.new("RGB", (1440, 2400), "white")
    ImageDraw.Draw(page).rectangle((0, 0, 1440, 600), fill=(194, 65, 12))  # an orange hero at the top
    page.save(path / "home.png")
    Image.new("RGB", (390, 844), (30, 120, 60)).save(path / "phone.png")
    (path / "notes.txt").write_text("hi")
    Image.new("RGB", (100, 80)).save(path / "tiny.png")
    return path


def ask(args, settings):
    return asyncio.run(dm.run_tool("make_mockup", args, settings))


def test_makes_three_mockups(s, folder):
    out = ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "file": "home.png", "address": "lebos.co.uk",
               "colour": "#c2410c"}, s)
    assert "mockup-browser.png, mockup-phone.png, mockup-combo.png" in out
    browser = Image.open(folder / "mockup-browser.png")
    assert browser.size == (1440 + 240, 900 + dm.BAR + 240)
    assert browser.getpixel((120 + 700, 120 + dm.BAR + 100)) == (194, 65, 12)  # the hero shows under the bar
    assert Image.open(folder / "mockup-combo.png").size == (1920, 1200)
    phone = Image.open(folder / "mockup-phone.png")
    assert phone.getpixel((phone.width // 2, 120 + 14 + 100)) == (194, 65, 12)


def test_separate_phone_screenshot(s, folder):
    ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "file": "home.png", "phone_file": "phone.png"}, s)
    phone = Image.open(folder / "mockup-phone.png")
    assert phone.getpixel((phone.width // 2, 120 + 14 + 300)) == (30, 120, 60)


def test_short_page_gets_white_below():
    out = dm.top(Image.new("RGB", (1440, 300), "black"), 1440, 900)
    assert out.size == (1440, 900) and out.getpixel((10, 10)) == (0, 0, 0) and out.getpixel((10, 800)) == (255,) * 3


def test_bad_input(s, folder):
    assert "Say which memory folder" in ask({}, s)
    assert "PNG, JPG or WebP" in ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "file": "notes.txt"}, s)
    assert "too small" in ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "file": "tiny.png"}, s)
    assert "isn't in this folder" in ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "file": "nope.png"}, s)
    assert "Can't read the colour" in ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "file": "home.png",
                                           "colour": "rust"}, s)


def test_registered():
    assert dm in tools.ABILITIES
