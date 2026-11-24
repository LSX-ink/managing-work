import asyncio
import re

import pytest

import design_signature as ds
import tools
from config import Settings
from design_contrast import AA, ratio

FULL = {"business": "Lebo's Bakery", "colour": "#fde047", "person": "Lebo Mokoena", "role": "Owner",
        "phone": "+44 7700 900123", "email": "hello@lebosbakery.co.uk", "website": "www.lebosbakery.co.uk",
        "socials": {"instagram": "instagram.com/lebosbakery", "TikTok": "https://www.tiktok.com/@lebosbakery"},
        "note": "Open Tue-Sat, 7am-3pm"}


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(ds.run_tool("make_email_signature", args, settings))


def test_full_signature(s, tmp_path):
    out = ask(FULL, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "email"
    assert "signature-lebo-mokoena.html" in out and "Gmail" in out
    page = (folder / "signature-lebo-mokoena.html").read_text()
    assert 'href="tel:+447700900123"' in page and 'href="mailto:hello@lebosbakery.co.uk"' in page
    assert 'href="https://www.lebosbakery.co.uk"' in page and ">lebosbakery.co.uk</a>" in page
    assert 'href="https://instagram.com/lebosbakery"' in page and ">TikTok</a>" in page
    assert "Lebo&#x27;s Bakery" in page and ">LB<" in page  # escaped business and initials tile
    assert "<style" not in page and "class=" not in page  # every style inline, so email apps keep it
    # a pale yellow brand still gives links that read on white
    links = set(re.findall(r"a href=\"[^\"]+\" style=\"color:(#[0-9a-f]{6})", page))
    assert links and all(ratio(c, "#ffffff") >= AA for c in links)
    text = (folder / "signature-lebo-mokoena.txt").read_text()
    assert text.startswith("--\nLebo Mokoena\nOwner | Lebo's Bakery\n+44 7700 900123")
    assert "Instagram: https://instagram.com/lebosbakery" in text and "Open Tue-Sat" in text


def test_business_only_with_logo(s, tmp_path):
    out = ask({"business": "Fade Inn", "colour": "#111827", "website": "fadeinn.co.uk",
               "logo_url": "https://fadeinn.co.uk/logo.png"}, s)
    assert "signature.html" in out
    page = (tmp_path / "Kinetic Web Designs" / "Fade Inn" / "email" / "signature.html").read_text()
    assert '<img src="https://fadeinn.co.uk/logo.png"' in page and 'alt="Fade Inn"' in page
    assert "color:#111827" in page  # a dark brand is used as it is


def test_escapes_html(s, tmp_path):
    ask({"business": "Tom & Co", "colour": "#2563eb", "person": "<b>Tom</b>", "email": "tom@tomco.com"}, s)
    page = (tmp_path / "Kinetic Web Designs" / "Tom & Co" / "email").glob("*.html")
    text = next(page).read_text()
    assert "<b>Tom</b>" not in text and "&lt;b&gt;Tom&lt;/b&gt;" in text and "Tom &amp; Co" in text


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000000", "email": "a@b.com"}, "business name"),
    ({"business": "X", "colour": "#000000"}, "at least one way"),
    ({"business": "X", "colour": "#000000", "email": "not-an-email"}, "isn't an email"),
    ({"business": "X", "colour": "#000000", "phone": "12"}, "too short"),
    ({"business": "X", "colour": "#000000", "website": "javascript:alert(1)"}, "isn't a web address"),
    ({"business": "X", "colour": "#000000", "website": "http://x.com"}, "isn't a web address"),
    ({"business": "X", "colour": "#000000", "socials": {"myspace": "myspace.com/x"}}, "Use these socials"),
    ({"business": "X", "colour": "#000000", "socials": {k: f"{k}.com/x" for k in
                                                         ("instagram", "tiktok", "facebook", "x", "youtube")}},
     "up to 4"),
    ({"business": "X", "colour": "#000000", "socials": "insta"}, "names and links"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert ds in tools.ABILITIES
    assert [t["name"] for t in ds.tool_definitions()] == ["make_email_signature"]
