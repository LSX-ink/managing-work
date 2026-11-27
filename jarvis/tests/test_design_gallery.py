import asyncio
import re

import pytest

import design_gallery as dg
import tools
from config import Settings
from design_contrast import AA, ratio

PHOTOS = [{"src": "/img/a.webp", "alt": "Lemon cake", "caption": "Lemon", "size": "1600x1200"},
          {"src": "https://x.com/b.jpg", "alt": "Chocolate cake", "full": "https://x.com/b-big.jpg"},
          {"src": "/img/c.webp", "alt": "Cupcakes"}]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dg.run_tool("make_gallery_section", {"name": "Lebo's Bakery", "colour": "#c2410c",
                                                            "photos": PHOTOS, **args}, settings))


def read(tmp_path, file="gallery.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_grid_gallery(s, tmp_path):
    out = ask({"intro": "Recent cakes.", "more_url": "https://instagram.com/lebo", "more_text": "More on Instagram"}, s)
    assert "landscape gallery" in out and "3 photos" in out and "Give each photo's size" not in out
    code = read(tmp_path)
    assert code.count('<li id="gi-') == 3 and code.count('class="g-view"') == 3
    assert '<img src="/img/a.webp" alt="Lemon cake" width="1600" height="1200" loading="lazy"' in code
    assert 'width="1200" height="900"' in code and "<figcaption>Lemon</figcaption>" in code
    assert '<img src="https://x.com/b-big.jpg" alt="Chocolate cake"' in code
    assert 'href="#g-3">Previous</a><a href="#g-2">Next</a><a href="#gi-1">Close</a>' in code
    assert "aspect-ratio: 4 / 3" in code and ".g-view:target" in code and "<script" not in code
    assert 'href="https://instagram.com/lebo" target="_blank" rel="noopener">More on Instagram<' in code
    assert read(tmp_path, "gallery-preview.html").startswith("<!doctype html>")


def test_masonry_and_square(s, tmp_path):
    out = ask({"layout": "masonry", "photos": [{"src": "/a.jpg", "alt": "A"}, {"src": "/b.jpg", "alt": "B"}]}, s)
    assert "masonry gallery" in out and "Give each photo's size" in out
    code = read(tmp_path)
    assert "columns: 3 16rem" in code and "aspect-ratio" not in code and "g-more\"" not in code.split("</style>")[1]
    ask({"layout": "square"}, s)
    assert "aspect-ratio: 1 / 1" in read(tmp_path)


@pytest.mark.parametrize("bad, msg", [
    ({"photos": PHOTOS[:1]}, "2 to 12"),
    ({"photos": PHOTOS * 5}, "2 to 12"),
    ({"photos": [{"alt": "x"}, PHOTOS[0]]}, "needs its address"),
    ({"photos": [{"src": "a.jpg", "alt": "x"}, PHOTOS[0]]}, "https:// address"),
    ({"photos": [{"src": "javascript:alert(1)", "alt": "x"}, PHOTOS[0]]}, "https:// address"),
    ({"photos": [{"src": "/a.jpg"}, PHOTOS[0]]}, "alt"),
    ({"photos": [{"src": "/a.jpg", "alt": "x", "size": "big"}, PHOTOS[0]]}, "1200x900"),
    ({"layout": "circle"}, "Layout can be"),
    ({"more_url": "mailto:a@b.c"}, "see more"),
])
def test_rejects(s, bad, msg):
    out = ask(bad, s)
    assert msg in out and "Made a" not in out


def test_escapes(s, tmp_path):
    ask({"photos": [{"src": "/a.jpg", "alt": "<b>x</b>", "caption": "<i>y</i>"}, PHOTOS[0]]}, s)
    code = read(tmp_path)
    assert "&lt;b&gt;x&lt;/b&gt;" in code and "<i>y" not in code


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours(brand):
    code = dg.block({"name": "X", "brand": brand, "layout": "square", "photos": [
        {"src": "/a", "full": "/a", "alt": "a", "caption": "", "w": 1, "h": 1}] * 2, "title": "T", "intro": "",
        "more_url": "", "more_text": ""})
    get = lambda k: re.search(rf"--g-{k}:(#[0-9a-f]{{6}})", code).group(1)  # noqa: E731
    assert ratio(get("accent"), "#ffffff") >= AA and ratio(get("light"), "#0b0b0f") >= AA


def test_registered():
    assert dg in tools.ABILITIES and [t["name"] for t in dg.tool_definitions()] == ["make_gallery_section"]
