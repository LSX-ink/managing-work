import asyncio

import pytest
from PIL import Image

import design_carousel as dc
import tools
from config import Settings
from design_contrast import UI, ratio

ARGS = {"name": "Kinetic Web Designs", "colour": "#4f46e5", "title": "3 signs your site is losing customers",
        "points": [{"heading": "Slow to load", "text": "Half of phone visitors leave."}, "No clear button",
                   {"heading": "Phone number is a picture"}], "handle": "kineticwebdesigns",
        "website": "https://www.kineticwebdesigns.co.uk", "slug": "signs"}


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dc.run_tool("make_carousel", args, settings))


def folder(tmp_path, name="Kinetic Web Designs", slug="signs"):
    return tmp_path / "Kinetic Web Designs" / name / "posts" / slug


def test_slides(s, tmp_path):
    out = ask(ARGS, s)
    f = folder(tmp_path)
    assert "5-slide carousel" in out and "Heads up" not in out
    slides = sorted(p.name for p in f.glob("*.png"))
    assert slides == ["01.png", "02.png", "03.png", "04.png", "05.png"]
    first, second = Image.open(f / "01.png").convert("RGB"), Image.open(f / "02.png").convert("RGB")
    assert first.size == dc.SIZE and first.getpixel((10, 600)) == (0x4f, 0x46, 0xe5)  # brand cover
    assert second.getpixel((10, 600)) != (0x4f, 0x46, 0xe5)  # point slides use the soft tint
    pdf = (f / "carousel.pdf").read_bytes()
    assert pdf.startswith(b"%PDF") and b"/Count 5" in pdf


def test_progress_bar_grows(s, tmp_path):
    ask(ARGS, s)
    f = folder(tmp_path)
    y = dc.SIZE[1] - 65

    def filled(name, colour_of):
        im = Image.open(f / name).convert("RGB")
        return sum(1 for x in range(dc.PAD, dc.SIZE[0] - dc.PAD) if im.getpixel((x, y)) == colour_of(im))

    on_ink = lambda im: im.getpixel((dc.PAD + 2, y))  # noqa: E731
    assert filled("02.png", on_ink) < filled("03.png", on_ink) < filled("04.png", on_ink)


def test_rerun_removes_stale_slides(s, tmp_path):
    ask(ARGS, s)
    ask({**ARGS, "points": ["Just one"]}, s)
    assert sorted(p.name for p in folder(tmp_path).glob("*.png")) == ["01.png", "02.png", "03.png"]


def test_pale_brand_number_reads_on_tint():
    image, _ = dc.point("#fde047", 1, "Store it cut side down", "", 2, 3, "")
    tint = "#%02x%02x%02x" % image.getpixel((10, 600))
    number = min((image.getpixel((x, 300)) for x in range(dc.PAD, 400)), key=sum)  # the solid middle of a digit
    assert ratio("#%02x%02x%02x" % number, tint) >= UI


def test_slug_cut_at_word(s, tmp_path):
    out = ask({**ARGS, "slug": None, "title": "3 signs your website is losing you customers every day"}, s)
    assert "posts/3-signs-your-website-is-losing-you:" in out


def test_long_point_is_flagged(s):
    out = ask({**ARGS, "points": [{"heading": "x", "text": "word " * 400}]}, s)
    assert "point 1" in out and "shortened" in out


@pytest.mark.parametrize("args, words", [
    ({**ARGS, "name": ""}, "brand or client name"),
    ({**ARGS, "title": ""}, "title"),
    ({**ARGS, "points": []}, "1 to 8 points"),
    ({**ARGS, "points": ["a"] * 9}, "1 to 8 points"),
    ({**ARGS, "points": "a, b"}, "as a list"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dc in tools.ABILITIES and [t["name"] for t in dc.tool_definitions()] == ["make_carousel"]
