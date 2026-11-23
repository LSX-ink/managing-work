import asyncio
import re

import pytest

import design_header as dh
import tools
from config import Settings
from design_contrast import AA, ratio

LINKS = [{"text": "Menu", "url": "/menu"}, {"text": "Cakes", "url": "/cakes"}, {"text": "Shop", "url": "https://s.x"}]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dh.run_tool("make_site_header", {"name": "Lebo's Bakery", "colour": "#c2410c", **args},
                                   settings))


def read(tmp_path, file="header.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_full_header(s, tmp_path):
    out = ask({"links": LINKS, "current": "cakes", "button": "Order now", "link": "/order"}, s)
    assert "3 menu links" in out and "Menu button" in out and 'id="main"' in out
    code = read(tmp_path)
    assert code.count('<nav') == 2 and code.count('aria-label="Main"') == 2 and "<details class=\"s-menu\">" in code
    assert code.count('href="/cakes" aria-current="page"') == 2 and 'href="/menu" aria-current' not in code
    assert '<a class="s-cta" href="/order">Order now</a>' in code and '<a class="s-skip" href="#main">' in code
    assert "position: sticky" in code and "<script" not in code
    assert '<span>Lebo&#x27;s Bakery</span>' in code
    assert 'id="main"' in read(tmp_path, "header-preview.html")


def test_logo_no_button_not_sticky(s, tmp_path):
    out = ask({"logo": "/img/logo.svg", "logo_height": 32, "sticky": False, "current": "Nope"}, s)
    assert "0 menu links" in out and "Add a main button" in out and "isn't one of the menu links" in out
    code = read(tmp_path)
    assert '<img src="/img/logo.svg" alt="Lebo&#x27;s Bakery" height="32"' in code
    assert "s-menu\">" not in code and 'class="s-cta"' not in code and "top: 0; z-index: 50" not in code


def test_fold_point_grows_with_links(s):
    few = dh.block({"name": "A", "brand": "#c2410c", "links": [("Menu", "/m")], "current": "", "button": "",
                    "link": "", "logo": "", "logo_height": 40, "home": "/", "sticky": True, "fold": 40})
    assert "max-width: 40rem" in few
    long = [{"text": f"Long page {i}", "url": f"/p{i}"} for i in range(7)]
    assert re.search(r"about (\d+)px", ask({"links": long, "button": "Book a table"}, s)).group(1) == "1024"


@pytest.mark.parametrize("bad, msg", [
    ({"links": [{"text": "a", "url": "javascript:alert(1)"}]}, "isn't one I can use"),
    ({"links": [{"text": "a"}]}, "needs its words"),
    ({"links": LINKS * 3}, "up to 7"),
    ({"links": [{"text": "A", "url": "/a"}, {"text": "a", "url": "/b"}]}, "same words"),
    ({"links": [{"text": "x" * 30, "url": "/a"}]}, "short"),
    ({"button": "y" * 30}, "under 24"),
    ({"logo": "logo.png"}, "logo"),
    ({"logo_height": 200}, "between 20 and 64"),
    ({"name": "n" * 50}, "under 40"),
])
def test_rejects(s, bad, msg):
    out = ask(bad, s)
    assert msg in out and "Made a header" not in out


def test_escapes(s, tmp_path):
    ask({"links": [{"text": "<b>x</b>", "url": "/a"}], "button": "<i>go</i>"}, s)
    code = read(tmp_path)
    assert "&lt;b&gt;x&lt;/b&gt;" in code and "<i>go" not in code


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours(brand):
    code = dh.block({"name": "X", "brand": brand, "links": [], "current": "", "button": "B", "link": "#",
                     "logo": "", "logo_height": 40, "home": "/", "sticky": True, "fold": 40})
    get = lambda k: re.search(rf"--s-{k}:(#[0-9a-f]{{6}})", code).group(1)  # noqa: E731
    assert ratio(get("brand"), get("on")) >= AA and ratio(get("accent"), "#ffffff") >= AA


def test_registered():
    assert dh in tools.ABILITIES and [t["name"] for t in dh.tool_definitions()] == ["make_site_header"]
