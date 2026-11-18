import asyncio

import pytest
from PIL import Image

import design_posts as dp
import tools
from config import Settings

BASE = {"name": "Lebo's Bakery", "colour": "#c2410c", "headline": "Fresh sourdough every morning",
        "text": "Baked at 5am in Croydon, gone by noon.", "cta": "Order now", "website": "https://www.lebos.co.uk/"}
BRAND = (0xc2, 0x41, 0x0c)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


@pytest.fixture
def folder(tmp_path):
    path = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery"
    path.mkdir(parents=True)
    Image.new("RGB", (1600, 1200), (30, 140, 200)).save(path / "bread.png")
    return path


def ask(args, settings):
    return asyncio.run(dp.run_tool("make_social_post", args, settings))


def test_post_and_story(s, tmp_path):
    out = ask(BASE, s)
    posts = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "posts"
    assert "fresh-sourdough-every-morning-post.png" in out and "Heads up" not in out
    post = Image.open(posts / "fresh-sourdough-every-morning-post.png")
    story = Image.open(posts / "fresh-sourdough-every-morning-story.png").convert("RGB")
    assert post.size == (1080, 1350) and story.size == (1080, 1920)
    assert post.getpixel((10, 1340)) == BRAND
    whites = sum(1 for y in range(dp.STORY_TOP, 1920 - dp.STORY_BOTTOM, 4) for x in range(0, 1080, 4)
                 if story.getpixel((x, y)) == (255, 255, 255))
    assert whites > 500  # the words and the button are drawn


def test_story_safe_zones_are_plain(s, tmp_path):
    ask(dict(BASE, formats=["story"]), s)
    story = Image.open(tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "posts" /
                       "fresh-sourdough-every-morning-story.png").convert("RGB")
    bottom = {story.getpixel((x, y)) for y in range(1920 - dp.STORY_BOTTOM, 1920, 3) for x in range(0, 1080, 3)}
    assert bottom == {BRAND}
    top = {story.getpixel((x, y)) for y in range(0, dp.STORY_TOP, 3) for x in range(0, 1080, 3)}
    assert top == {BRAND}


def test_photo(s, folder):
    out = ask(dict(BASE, folder="Kinetic Web Designs/Lebo's Bakery", photo="bread.png", slug="Launch Day!"), s)
    assert "using the photo bread.png" in out
    post = Image.open(folder / "posts" / "launch-day-post.png")
    assert post.getpixel((540, 300)) == (30, 140, 200) and post.getpixel((10, 1340)) == BRAND
    story = Image.open(folder / "posts" / "launch-day-story.png")
    assert story.getpixel((540, 100)) == (30, 140, 200)  # photo shows clear at the top
    r, g, b = story.getpixel((540, 1900))
    assert r + g + b < 120  # dark fade at the bottom so white words read


def test_long_headline_is_shortened(s):
    out = ask(dict(BASE, formats=["post"], headline="word " * 60), s)
    assert "Heads up: the headline didn't fit" in out


def test_bad_input(s, folder):
    assert "Give the brand" in ask({"colour": "#000", "headline": "Hi"}, s)
    assert "short headline" in ask({"name": "A", "colour": "#000"}, s)
    assert "24 letters" in ask(dict(BASE, cta="x" * 30), s)
    assert "Pick post, story or both" in ask(dict(BASE, formats=["reel"]), s)
    assert "which memory folder" in ask(dict(BASE, photo="bread.png"), s)
    (folder / "notes.txt").write_text("x")
    assert "PNG, JPG or WebP" in ask(dict(BASE, folder="Kinetic Web Designs/Lebo's Bakery", photo="notes.txt"), s)
    assert "Can't read the colour" in ask(dict(BASE, colour="nope"), s)


def test_registered():
    assert dp in tools.ABILITIES
