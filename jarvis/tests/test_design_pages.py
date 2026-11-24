import asyncio
import re

import pytest

import design_pages as dp
import tools
from config import Settings
from design_contrast import AA, ratio


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dp.run_tool("make_site_page", {"name": "Lebo's Bakery", "colour": "#c2410c", **args}, settings))


def read(tmp_path, file):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_not_found_page(s, tmp_path):
    out = ask({"search_url": "/search", "links": [{"label": "Menu", "url": "/menu"}, {"label": "Order",
                                                                                     "url": "https://x.co/o"}],
               "email": "hello@lebos.co.uk"}, s)
    assert "404.html" in out and "Cloudflare Pages" in out
    page = read(tmp_path, "404.html")
    assert "We can&#x27;t find that page" in page and 'href="/"' in page and 'action="/search"' in page
    assert 'href="/menu">Menu<' in page and 'href="https://x.co/o"' in page and "mailto:hello@lebos.co.uk" in page
    assert '<meta name="robots" content="noindex">' in page and ">LB<" in page and "<script>" not in page


def test_coming_soon_with_countdown(s, tmp_path):
    ask({"kind": "coming-soon", "date": "2026-12-01 09:00", "instagram": "@lebos.bakery", "phone": "0121 496 0000"}, s)
    page = read(tmp_path, "coming-soon.html")
    assert "Lebo&#x27;s Bakery is coming soon" in page and "noindex" not in page
    assert 'Opening <time datetime="2026-12-01T09:00:00">Tuesday 1 December 2026 at 09:00</time>' in page
    assert 'id="count"' in page and 'new Date("2026-12-01T09:00:00")' in page
    assert "https://instagram.com/lebos.bakery" in page and 'href="tel:01214960000"' in page


def test_maintenance_page(s, tmp_path):
    ask({"kind": "maintenance", "date": "2026-11-20", "text": ""}, s)
    page = read(tmp_path, "maintenance.html")
    assert "We&#x27;ll be back shortly" in page and "noindex" in page and 'class="lead"' not in page
    assert "Back by <time" in page and "Friday 20 November 2026</time>" in page and 'id="count"' not in page


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours_pass_aa(s, tmp_path, brand):
    asyncio.run(dp.run_tool("make_site_page", {"name": "Shop", "colour": brand}, s))
    page = (tmp_path / "Kinetic Web Designs" / "Shop" / "web" / "404.html").read_text(encoding="utf-8")
    get = lambda k: re.search(rf"--{k}: (#[0-9a-f]{{6}});", page).group(1)  # noqa: E731
    assert ratio(get("brand"), get("on-brand")) >= AA and ratio(get("accent"), "#ffffff") >= AA


def test_escapes_text(s, tmp_path):
    ask({"headline": "<script>x</script>", "text": "a & b"}, s)
    page = read(tmp_path, "404.html")
    assert "<script>x" not in page and "&lt;script&gt;x" in page and "a &amp; b" in page


@pytest.mark.parametrize("args, words", [
    ({"name": ""}, "business name"),
    ({"kind": "gone"}, "Pick a page"),
    ({"home": "javascript:alert(1)"}, "isn't a link"),
    ({"links": [{"label": "a", "url": "/a"}] * 5}, "up to 4"),
    ({"links": [{"label": "a"}]}, "label and a url"),
    ({"date": "next week", "kind": "coming-soon"}, "2026-12-01"),
    ({"date": "2026-12-01"}, "only fits"),
    ({"email": "nope"}, "email"),
    ({"phone": "12"}, "too short"),
    ({"instagram": "bad handle!"}, "Instagram"),
    ({"headline": "x" * 81}, "under 80"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dp in tools.ABILITIES and [t["name"] for t in dp.tool_definitions()] == ["make_site_page"]
