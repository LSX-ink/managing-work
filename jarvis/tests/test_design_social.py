import asyncio

import pytest
from PIL import Image

import design_social as ds
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(ds.run_tool("make_share_card", args, settings))


def test_card_and_tags(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#c2410c", "title": "Fresh bread in Croydon",
               "description": "Sourdough & pastries baked every morning.", "url": "https://www.lebosbakery.co.uk"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "share"
    assert "share-home.png" in out and "Heads up" not in out
    image = Image.open(folder / "share-home.png")
    assert image.size == (1200, 630)
    assert image.getpixel((5, 620)) == (0xc2, 0x41, 0x0c)
    tags = (folder / "meta-tags-home.html").read_text()
    assert '<meta property="og:image" content="https://www.lebosbakery.co.uk/share-home.png">' in tags
    assert 'content="summary_large_image"' in tags and "Sourdough &amp; pastries" in tags
    assert '<link rel="canonical" href="https://www.lebosbakery.co.uk">' in tags


def test_long_text_is_fitted_and_warned(s, tmp_path):
    out = ask({"name": "X", "colour": "#111827", "page": "Pricing", "title": "word " * 40,
               "description": "d" * 200}, s)
    assert "Google may cut it" in out and "shows in full" in out
    assert (tmp_path / "Kinetic Web Designs" / "X" / "share" / "share-pricing.png").exists()
    tags = (tmp_path / "Kinetic Web Designs" / "X" / "share" / "meta-tags-pricing.html").read_text()
    assert "change og:image to its full web address" in tags and "canonical" not in tags


def test_fit_adds_ellipsis():
    from PIL import ImageDraw
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    size, lines = ds.fit(draw, "word " * 60, 400, (40, 30), 2, True)
    assert size == 30 and len(lines) == 2 and lines[-1].endswith("...")


def test_site_of():
    assert ds.site_of("https://www.kineticwebdesigns.co.uk/pricing") == "kineticwebdesigns.co.uk"
    assert ds.site_of("lebos.co.uk") == "lebos.co.uk" and ds.site_of("") == ""


def test_bad_input(s):
    assert "Give the brand" in ask({"colour": "#000"}, s)
    assert "Can't read the colour" in ask({"name": "X", "colour": "orangey"}, s)


def test_registered():
    assert ds in tools.ABILITIES
