import asyncio
import json

import pytest
from PIL import Image

import design_icons as di
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(di.run_tool("make_app_icons", args, settings))


def test_initials_icon_set(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#c2410c"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "icons"
    assert "initials LB" in out and "Heads up" not in out
    sizes = {"favicon-32.png": 32, "apple-touch-icon.png": 180, "icon-192.png": 192, "icon-512.png": 512,
             "icon-maskable-512.png": 512}
    for name, size in sizes.items():
        assert Image.open(folder / name).size == (size, size)
    with Image.open(folder / "favicon.ico") as ico:
        assert {(16, 16), (32, 32), (48, 48)} <= set(ico.info["sizes"])
    rounded = Image.open(folder / "icon-512.png").convert("RGBA")
    assert rounded.getpixel((2, 2))[3] == 0 and rounded.getpixel((256, 20))[:3] == (0xc2, 0x41, 0x0c)
    for full in ("apple-touch-icon.png", "icon-maskable-512.png"):  # solid to the corners
        image = Image.open(folder / full)
        assert image.mode == "RGB" and image.getpixel((1, 1)) == (0xc2, 0x41, 0x0c)
    data = json.loads((folder / "site.webmanifest").read_text())
    assert data["short_name"] == "Lebo's" and data["theme_color"] == "#c2410c"
    assert [i["src"] for i in data["icons"]] == ["icon-192.png", "icon-512.png", "icon-maskable-512.png"]
    assert data["icons"][2]["purpose"] == "maskable"
    tags = (folder / "head-tags.html").read_text()
    assert 'rel="apple-touch-icon"' in tags and 'href="/site.webmanifest"' in tags and "#c2410c" in tags
    assert "circle crop" in (folder / "icons.html").read_text()


def test_maskable_letters_stay_in_safe_zone():
    image = di.tile("WW", "#111827", 512, rounded=False, scale=0.8)
    box = Image.new("RGBA", image.size, (0x11, 0x18, 0x27, 255))
    bbox = Image.eval(Image.composite(image, box, image).convert("L"), lambda v: 255 if v > 128 else 0).getbbox()
    cx = cy = 256
    for x, y in ((bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3])):
        assert ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 <= 512 * di.SAFE / 2


def test_logo_picture(s, tmp_path):
    folder = tmp_path / "Kinetic Web Designs" / "Fade Inn"
    folder.mkdir(parents=True)
    Image.new("RGB", (400, 200), (20, 160, 80)).save(folder / "logo.png")
    out = ask({"name": "Fade Inn Barbers London", "colour": "#111111", "folder": "Kinetic Web Designs/Fade Inn",
               "file": "logo.png", "background": "#fafafa"}, s)
    assert "the logo logo.png" in out
    icons = tmp_path / "Kinetic Web Designs" / "Fade Inn Barbers London" / "icons"
    big = Image.open(icons / "icon-512.png").convert("RGB")
    assert big.getpixel((256, 256)) == (20, 160, 80) and big.getpixel((256, 40)) == (250, 250, 250)
    touch = Image.open(icons / "apple-touch-icon.png")
    assert touch.getpixel((0, 0)) == (250, 250, 250)
    assert json.loads((icons / "site.webmanifest").read_text())["short_name"] == "Fade"


def test_bad_input(s, tmp_path):
    folder = tmp_path / "Kinetic Web Designs" / "X"
    folder.mkdir(parents=True)
    Image.new("RGB", (100, 100)).save(folder / "tiny.png")
    (folder / "logo.svg").write_text("<svg/>")
    assert "too small" in ask({"name": "X", "colour": "#000", "folder": "Kinetic Web Designs/X", "file": "tiny.png"}, s)
    assert "export it as a PNG" in ask({"name": "X", "colour": "#000", "folder": "Kinetic Web Designs/X",
                                        "file": "logo.svg"}, s)
    assert "which memory folder" in ask({"name": "X", "colour": "#000", "file": "logo.png"}, s)
    assert "Can't read the colour" in ask({"name": "X", "colour": "nope"}, s)
    assert "Give the brand" in ask({"name": " ", "colour": "#000"}, s)
    assert "cut it after about 12" in ask({"name": "X", "colour": "#000", "short_name": "A very long label"}, s)


def test_registered():
    assert di in tools.ABILITIES
