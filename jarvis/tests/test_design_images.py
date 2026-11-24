import asyncio
import random

import pytest
from PIL import Image

import design_images as dimg
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


@pytest.fixture
def photos(tmp_path):
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery"
    folder.mkdir(parents=True)
    rng = random.Random(1)
    big = Image.new("RGB", (2000, 1000))
    big.putdata([(rng.randrange(256), 120, 60) for _ in range(2000 * 1000)])
    exif = Image.Exif()
    exif[0x0112] = 6  # stored sideways: turn 90 degrees clockwise to show
    exif[0x8825] = {1: "N", 2: (51.0, 30.0, 0.0)}  # GPS
    exif[0x0110] = "Pixel 9"
    big.save(folder / "Shop Front.jpg", quality=95, exif=exif)
    Image.new("RGBA", (300, 200), (0, 0, 0, 0)).save(folder / "logo.png")
    (folder / "notes.txt").write_text("not a picture")
    return folder


def ask(args, settings):
    return asyncio.run(dimg.run_tool("make_web_images", args, settings))


def test_whole_folder(s, photos):
    out = ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "alt": "Lebo's shop & counter"}, s)
    web = photos / "web"
    assert "2 pictures" in out and "GPS" in out
    names = sorted(p.name for p in web.iterdir())
    assert names == ["logo-300.png", "logo-300.webp", "pictures.html", "shop-front-1000.jpg", "shop-front-1000.webp",
                     "shop-front-480.webp", "shop-front-960.webp"]
    turned = Image.open(web / "shop-front-960.webp")
    assert turned.size == (960, 1920)  # turned upright: 1000 wide, 2000 tall, then scaled
    for name in ("shop-front-1000.jpg", "shop-front-1000.webp"):
        info = Image.open(web / name).getexif()
        assert 0x8825 not in info and 0x0110 not in info
    assert Image.open(web / "logo-300.png").mode == "RGBA"
    doc = (web / "pictures.html").read_text()
    assert 'srcset="logo-300.webp 300w"' in doc
    assert "shop-front-480.webp 480w, shop-front-960.webp 960w, shop-front-1000.webp 1000w" in doc
    assert 'width="1000" height="2000"' in doc and "Lebo&#x27;s shop &amp; counter" in doc
    assert doc.count('fetchpriority="high"') == 1 and 'loading="lazy"' in doc  # first picture loads first


def test_one_file_and_options(s, photos):
    out = ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "file": "Shop Front.jpg", "widths": [320, 5000, 640],
               "quality": 60, "sizes": "(min-width: 1024px) 50vw, 100vw"}, s)
    assert "1 picture " in out and "320, 640px wide" in out and "5000" not in out
    doc = (photos / "web" / "pictures.html").read_text()
    assert 'sizes="(min-width: 1024px) 50vw, 100vw"' in doc and 'alt="Shop Front"' in doc


def test_widths():
    assert dimg.widths(2000, (480, 960, 1600)) == [480, 960, 1600]
    assert dimg.widths(700, (480, 960, 1600)) == [480, 700]
    assert dimg.widths(300, (480, 960)) == [300]
    with pytest.raises(ValueError):
        dimg.widths(1000, [10])


def test_bad_input(s, photos, tmp_path):
    (tmp_path / "Kinetic Web Designs" / "Empty").mkdir()
    assert "Say which memory folder" in ask({}, s)
    assert "no PNG, JPG or WebP" in ask({"folder": "Kinetic Web Designs/Empty"}, s)
    assert "Use PNG, JPG or WebP" in ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "file": "notes.txt"}, s)
    assert "quality between 40 and 95" in ask({"folder": "Kinetic Web Designs/Lebo's Bakery", "quality": 10}, s)
    (photos / "broken.jpg").write_bytes(b"nope")
    assert "couldn't open broken.jpg" in ask({"folder": "Kinetic Web Designs/Lebo's Bakery"}, s)


def test_registered():
    assert dimg in tools.ABILITIES
