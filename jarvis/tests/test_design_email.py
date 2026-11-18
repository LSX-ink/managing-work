import asyncio

import pytest

import design_email as de
import tools
from config import Settings
from design_contrast import AA, UI, ratio


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(de.run_tool("make_email_template", args, settings))


def test_welcome_email(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#c2410c", "template": "Welcome", "subject": "Welcome to Lebo's",
               "preheader": "Your first loaf is on us: here's how to claim it this week.",
               "heading": "Fresh bread & a warm welcome", "message": "Hi there,\n\nThanks for joining.\nSee you soon!",
               "button_text": "Claim your loaf", "button_url": "lebosbakery.co.uk/offer"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "email"
    page = (folder / "welcome.html").read_text()
    assert "welcome.html" in out and "Heads up" not in out
    assert 'href="https://lebosbakery.co.uk/offer"' in page and "Claim your loaf" in page
    assert "Fresh bread &amp; a warm welcome" in page and "Thanks for joining.<br>See you soon!" in page
    assert page.count("<p style=") >= 3 and "<title>Welcome to Lebo&#x27;s</title>" in page
    assert 'role="presentation"' in page and "prefers-color-scheme: dark" in page and ">LB<" in page
    assert "Your first loaf is on us" in page.split("<table")[0]
    text = (folder / "welcome.txt").read_text()
    assert text.startswith("Subject: Welcome to Lebo's") and "Claim your loaf: https://lebosbakery.co.uk/offer" in text


@pytest.mark.parametrize("brand", ["#c2410c", "#fde047", "#22c55e", "#808080", "#000000", "#ffffff"])
def test_button_colours_read(brand):
    c = de.colours(brand)
    assert ratio(c["label"], c["button"]) >= AA
    assert ratio(c["button"], "#ffffff") >= UI
    assert ratio(c["link"], "#ffffff") >= AA and ratio(c["dark_link"], "#18181b") >= AA


def test_light_brand_and_notes(s, tmp_path):
    out = ask({"name": "Sunny", "colour": "#fde047", "message": "Hello", "button_text": "Go",
               "subject": "s" * 70, "preheader": "short"}, s)
    assert "too light for a button" in out and "phones show about 60" in out and "40-130 shows best" in out
    assert "button was left out" in out
    assert "Go</a>" not in (tmp_path / "Kinetic Web Designs" / "Sunny" / "email" / "email.html").read_text()


def test_logo_and_bad_input(s):
    page = de.build("A", "#123456", "s", "h", "m", "", "", "", "f", "https://a.co/logo.png", "A")
    assert '<img src="https://a.co/logo.png"' in page
    assert "full https:// link" in ask({"name": "A", "colour": "#123456", "message": "m", "button_text": "Go",
                                        "button_url": "javascript:alert(1)"}, s)
    bad = {"name": "A", "colour": "#123456", "message": "m", "button_url": "http://a.co"}
    assert "full https:// link" in ask(bad, s)
    assert "logo needs an https" in ask({"name": "A", "colour": "#123456", "message": "m", "logo_url": "tel:123"}, s)
    assert "the message" in ask({"name": "A", "colour": "#123456"}, s)
    assert "Can't read the colour" in ask({"name": "A", "colour": "blurple", "message": "m"}, s)
    assert de.link("mailto:hi@a.co") == "mailto:hi@a.co"


def test_registered():
    assert de in tools.ABILITIES
