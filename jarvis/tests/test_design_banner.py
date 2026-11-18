import asyncio

import pytest
from PIL import Image

import design_banner as db
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(db.run_tool("make_social_banners", args, settings))


def text_outside_safe_box(image, box, ink, slack=6):
    left, top, right, bottom = box
    px = image.load()
    for y in range(0, image.height, 2):
        for x in range(0, image.width, 2):
            inside = left - slack <= x <= right + slack and top - slack <= y <= bottom + slack
            if not inside and sum(abs(a - b) for a, b in zip(px[x, y], ink)) < 30:
                return (x, y)
    return None


@pytest.mark.parametrize("name, tagline", [
    ("Kinetic Web Designs", "Websites that win you customers"),
    ("Mama Lebo's Family Bakery and Coffee House Birmingham", "Fresh bread, good coffee and kind "
                                                                          "people every single day of the week"),
])
def test_all_four_stay_in_safe_area(s, tmp_path, name, tagline):
    out = ask({"name": name, "colour": "#4f46e5", "tagline": tagline, "website": "https://www.example.co.uk"}, s)
    assert "Made 4 social banners" in out
    folder = next((tmp_path / "Kinetic Web Designs").glob("*/social"))
    for site, file in db.FILES.items():
        image = Image.open(folder / file).convert("RGB")
        assert image.size == db.SITES[site][0]
        assert text_outside_safe_box(image, db.SITES[site][1], (255, 255, 255)) is None, site


def test_pick_sites_and_dark_text_on_pale_brand(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#fde047", "sites": ["linkedin", "LinkedIn", "x"]}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "social"
    assert "Made 2 social banners" in out and sorted(p.name for p in folder.iterdir()) == ["linkedin-banner.png",
                                                                                          "x-header.png"]
    image = Image.open(folder / "linkedin-banner.png").convert("RGB")
    assert image.crop(db.SITES["linkedin"][1]).convert("L").getextrema()[0] < 80  # dark words on yellow


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000"}, "business name"),
    ({"name": "X", "colour": "#000", "tagline": "x" * 91}, "90 letters"),
    ({"name": "X", "colour": "#000", "sites": ["myspace"]}, "Pick from"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert db in tools.ABILITIES and [t["name"] for t in db.tool_definitions()] == ["make_social_banners"]
