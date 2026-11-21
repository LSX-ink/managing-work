import asyncio
import re

import pytest

import design_hero as dh
import tools
from config import Settings
from design_contrast import AA, ratio


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dh.run_tool("make_hero_section", {"name": "Lebo's Bakery", "colour": "#c2410c",
                                                         "headline": "Fresh sourdough, baked every morning", **args},
                                   settings))


def read(tmp_path, file="hero.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_photo_hero(s, tmp_path):
    out = ask({"kicker": "Hockley", "line": "Real bread.", "button": "Order", "link": "/order",
               "button2": "Menu", "link2": "/menu", "proof": "★ 4.9 on Google", "image": "/img/shop.webp",
               "alt": "Loaves on the counter", "image_size": "1600x1000"}, s)
    assert "photo hero" in out and "make_web_images" in out
    code = read(tmp_path)
    assert 'class="hero split"' in code and '<h1 id="h-title">Fresh sourdough, baked every morning</h1>' in code
    assert '<a class="h-btn" href="/order">Order</a>' in code and '<a class="h-btn ghost" href="/menu">Menu</a>' in code
    assert 'src="/img/shop.webp" alt="Loaves on the counter" width="1600" height="1000" fetchpriority="high"' in code
    assert "★ 4.9 on Google" in code and ">Hockley<" in code and "prefers-reduced-motion" in code
    assert "<script" not in code and read(tmp_path, "hero-preview.html").startswith("<!doctype html>")
    assert code.index("<h1") < code.index("<img")  # words first, so phones show the headline first


def test_centred_defaults(s, tmp_path):
    out = ask({}, s)
    assert "centred hero" in out
    code = read(tmp_path)
    assert 'class="hero centre"' in code and 'href="#contact">Get in touch<' in code
    assert "ghost" not in code.split("</style>")[1] and "<img" not in code and "h-proof\">" not in code


def test_long_headline_tip(s):
    assert "4 to 10 words" in ask({"headline": "We bake really very nice fresh sourdough bread for you every single "
                                               "morning here"}, s)


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours(brand):
    code = dh.block({"name": "X", "brand": brand, "headline": "H", "line": "", "button": "B", "link": "#",
                     "button2": "", "link2": "", "proof": "", "kicker": "", "image": "", "alt": "", "w": 1, "h": 1})
    get = lambda k: re.search(rf"--h-{k}:(#[0-9a-f]{{6}})", code).group(1)  # noqa: E731
    assert ratio(get("brand"), get("on")) >= AA and ratio(get("accent"), get("tint")) >= AA


def test_escapes(s, tmp_path):
    ask({"headline": "<script>x</script>", "line": "a & b", "proof": "<b>p</b>", "button": "<i>go</i>"}, s)
    code = read(tmp_path)
    assert "<script>x" not in code and "a &amp; b" in code and "<b>p" not in code and "<i>go" not in code


@pytest.mark.parametrize("args, words", [
    ({"name": ""}, "business name"),
    ({"headline": ""}, "headline"),
    ({"headline": "x" * 91}, "under 90"),
    ({"line": "x" * 221}, "under 220"),
    ({"link": "javascript:alert(1)"}, "main button"),
    ({"button2": "More", "link2": "javascript:x"}, "second button"),
    ({"image": "http://x.com/a.jpg", "alt": "a"}, "photo"),
    ({"image": "/a.jpg"}, "alt"),
    ({"image": "/a.jpg", "alt": "a", "image_size": "big"}, "1200x900"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dh in tools.ABILITIES and [t["name"] for t in dh.tool_definitions()] == ["make_hero_section"]
