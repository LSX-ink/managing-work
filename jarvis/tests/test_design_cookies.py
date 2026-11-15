import asyncio
import re

import pytest

import design_cookies as dc
import tools
from config import Settings
from design_contrast import AA, ratio


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dc.run_tool("make_cookie_banner", args, settings))


def web(tmp_path, name):
    return tmp_path / "Kinetic Web Designs" / name / "web"


def test_makes_banner_and_demo(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#c2410c", "kinds": ["analytics", "Marketing", "analytics"],
               "policy_url": "/cookies"}, s)
    assert "optional cookies (analytics, marketing)" in out and "isn't legal advice" in out
    banner = (web(tmp_path, "Lebo's Bakery") / "cookie-banner.html").read_text(encoding="utf-8")
    demo = (web(tmp_path, "Lebo's Bakery") / "cookie-demo.html").read_text(encoding="utf-8")
    assert banner.startswith("<!-- Cookie banner for Lebo&#x27;s Bakery") and 'data-cookies="analytics"' in banner
    assert "Cookies on Lebo&#x27;s Bakery" in banner and 'href="/cookies"' in banner
    assert 'data-kind="analytics"' in banner and 'data-kind="marketing"' in banner
    assert 'data-kind="preferences"' not in banner
    assert "KINDS = ['analytics', 'marketing']" in banner
    assert demo.startswith("<!doctype html>") and banner.split("-->\n", 1)[1].strip() in demo


def test_accept_and_reject_look_the_same(s, tmp_path):
    ask({"name": "Shop", "colour": "#4f46e5"}, s)
    banner = (web(tmp_path, "Shop") / "cookie-banner.html").read_text(encoding="utf-8")
    assert ".ck .ck-yes, .ck .ck-no {" in banner  # one shared style, so neither is easier
    assert banner.index("Accept all") < banner.index("Reject all") < banner.index(">Choose<")


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours_pass_aa(brand):
    style = dc.css(brand, "bottom")
    button, words = re.search(r"\.ck-no \{ background: (#\w+); color: (#\w+)", style).groups()
    accent = re.search(r"\.ck a \{ color: (#\w+)", style).group(1)
    assert ratio(button, words) >= AA and ratio(accent, "#ffffff") >= AA


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000"}, "business name"),
    ({"name": "X", "colour": "#000", "kinds": ["tracking"]}, "Cookie kinds"),
    ({"name": "X", "colour": "#000", "policy_url": "javascript:alert(1)"}, "cookie policy"),
    ({"name": "X", "colour": "#000", "policy_url": 'https://a.com/"><script>'}, "cookie policy"),
    ({"name": "X", "colour": "#000", "position": "top"}, "Position can be"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_name_is_escaped(s, tmp_path):
    ask({"name": "A <b> & Co", "colour": "#333"}, s)
    banner = next((tmp_path / "Kinetic Web Designs").glob("*/web/cookie-banner.html")).read_text(encoding="utf-8")
    assert "<b>" not in banner and "A &lt;b&gt; &amp; Co" in banner


def test_registered():
    assert dc in tools.ABILITIES and [t["name"] for t in dc.tool_definitions()] == ["make_cookie_banner"]
