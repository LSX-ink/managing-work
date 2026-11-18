import asyncio
import re

import pytest

import design_linkpage as dl
import tools
from config import Settings
from design_contrast import AA, ratio


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dl.run_tool("make_link_page", args, settings))


def page_of(tmp_path, name):
    return (tmp_path / "Kinetic Web Designs" / name / "web" / "links.html").read_text(encoding="utf-8")


def test_makes_page_with_buttons_socials_and_whatsapp(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#c2410c", "tagline": "Fresh bread daily",
               "links": [{"label": "Order online", "url": "lebosbakery.co.uk/order"},
                         {"label": "Call us", "url": "tel:+44 121 496 0000"}],
               "whatsapp": "+44 7700 900123", "socials": {"instagram": "@lebosbakery", "TikTok": "lebos"}}, s)
    assert "3 buttons and 2 social links" in out
    page = page_of(tmp_path, "Lebo's Bakery")
    assert 'href="https://lebosbakery.co.uk/order" target="_blank" rel="noopener"' in page
    assert 'href="tel:+44 121 496 0000">' in page
    assert "https://wa.me/447700900123" in page and "https://instagram.com/lebosbakery" in page
    assert "https://www.tiktok.com/@lebos" in page
    assert "Lebo&#x27;s Bakery" in page and ">LB<" in page
    assert "prefers-color-scheme: dark" in page and "prefers-reduced-motion" in page


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_button_words_pass_aa(s, tmp_path, brand):
    ask({"name": "Shop", "colour": brand, "links": [{"label": "Shop", "url": "https://example.com"}]}, s)
    page = page_of(tmp_path, "Shop")
    button = re.search(r"--brand: (#[0-9a-f]{6})", page).group(1)
    words = re.search(r"--on-brand: (#[0-9a-f]{6})", page).group(1)
    accent = re.search(r"--accent: (#[0-9a-f]{6})", page).group(1)
    assert ratio(button, words) >= AA and ratio(accent, "#ffffff") >= AA


def test_escapes_and_blocks_bad_links(s, tmp_path):
    ask({"name": "A<b>", "colour": "#333", "tagline": "<script>alert(1)</script>",
         "links": [{"label": "<img src=x>", "url": "https://example.com/?a=1&b=2"}]}, s)
    page = next((tmp_path / "Kinetic Web Designs").glob("*/web/links.html")).read_text(encoding="utf-8")
    assert "<script>" not in page and "<img src=x>" not in page and "a=1&amp;b=2" in page
    for url in ("javascript:alert(1)", "http://example.com", "data:text/html,hi", 'https://x.com/"onmouseover='):
        assert "isn't a link" in ask({"name": "B", "colour": "#333", "links": [{"label": "x", "url": url}]}, s)


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000", "links": [{"label": "a", "url": "https://a.com"}]}, "business name"),
    ({"name": "X", "colour": "#000", "links": []}, "1 to 8"),
    ({"name": "X", "colour": "#000", "links": [{"label": "a", "url": "https://a.com"}] * 9}, "1 to 8"),
    ({"name": "X", "colour": "#000", "links": ["https://a.com"]}, "label and a url"),
    ({"name": "X", "colour": "#000", "links": [{"label": "a", "url": "https://a.com"}], "whatsapp": "123"},
     "country code"),
    ({"name": "X", "colour": "#000", "links": [{"label": "a", "url": "https://a.com"}], "socials": {"myspace": "a"}},
     "Socials can be"),
    ({"name": "X", "colour": "#000", "links": [{"label": "a", "url": "https://a.com"}],
      "socials": {"instagram": "bad handle!"}}, "handle"),
    ({"name": "X", "colour": "#000", "links": [{"label": "a", "url": "https://a.com"}], "logo": "tel:12345"},
     "https:// image"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dl in tools.ABILITIES and [t["name"] for t in dl.tool_definitions()] == ["make_link_page"]
