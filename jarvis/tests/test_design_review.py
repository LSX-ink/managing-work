import asyncio

import pytest
from PIL import Image

import design_review as dr
import tools
from config import Settings

GOOD = {"name": "Fade Inn", "colour": "#111827", "reviewer": "Jordan T.", "website": "https://www.fadeinn.co.uk",
        "quote": "Best fade I have had in Birmingham. Booked again before I left!"}


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dr.run_tool("make_review_post", args, settings))


def test_post_and_story(s, tmp_path):
    out = ask(GOOD, s)
    folder = tmp_path / "Kinetic Web Designs" / "Fade Inn" / "posts"
    assert "5 stars review post from Jordan T." in out and "shortened" not in out
    post = Image.open(folder / "review-jordan-t-post.png").convert("RGB")
    story = Image.open(folder / "review-jordan-t-story.png").convert("RGB")
    assert post.size == dr.POST and story.size == dr.STORY
    assert post.getpixel((5, post.height - 5)) == (0x11, 0x18, 0x27)  # brand background
    assert post.getpixel((post.width // 2, post.height // 2)) == (255, 255, 255)  # the white card


def test_half_star():
    image = Image.new("RGB", (600, 100), (255, 255, 255))
    dr.stars(image, 10, 50, 4.5)
    r = 30
    fifth = 10 + r + 4 * (2 * r + 14)
    assert image.getpixel((round(fifth - r * 0.2), 50)) == dr.GOLD  # left half gold
    assert image.getpixel((round(fifth + r * 0.2), 50)) == dr.EMPTY  # right half grey
    assert image.getpixel((10 + r, 50)) == dr.GOLD


def test_shorten_at_sentence_end():
    text = "Lovely bread. " * 50
    short, cut = dr.shorten(text.strip(), 120)
    assert cut and short.endswith("bread...") and len(short) <= 123
    assert dr.shorten("Short and sweet.", 120) == ("Short and sweet.", False)


def test_long_review_is_shortened(s):
    out = ask({**GOOD, "quote": "Lovely sourdough and friendly staff. " * 30, "formats": ["post"], "stars": 4.5}, s)
    assert "4.5 stars" in out and "shortened" in out


@pytest.mark.parametrize("args, words", [
    ({**GOOD, "name": ""}, "business name"),
    ({**GOOD, "quote": ""}, "review words"),
    ({**GOOD, "reviewer": ""}, "reviewer's name"),
    ({**GOOD, "stars": 6}, "1 to 5"),
    ({**GOOD, "stars": 4.3}, "in halves"),
    ({**GOOD, "formats": ["reel"]}, "post, story or both"),
    ({**GOOD, "quote": "word " * 401}, "very long"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dr in tools.ABILITIES and [t["name"] for t in dr.tool_definitions()] == ["make_review_post"]
