import asyncio
import re

import pytest

import design_pricing as dp
import tools
from config import Settings
from design_contrast import AA, ratio

PLANS = [{"name": "Starter", "price": 395, "features": ["1 page", {"text": "Booking", "included": False}]},
         {"name": "Business", "price": "1,595.5", "popular": True, "period": "month", "link": "/buy"},
         {"name": "Custom", "price": "Ask us", "button": "Talk to us"}]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dp.run_tool("make_pricing_table", {"name": "Lebo's Bakery", "colour": "#c2410c", **args},
                                   settings))


def read(tmp_path, file="pricing.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_makes_table(s, tmp_path):
    out = ask({"plans": PLANS, "note": "Pay half to start."}, s)
    assert "3 plans" in out and "Business is marked Most popular" in out
    code = read(tmp_path)
    assert code.count('<article class="plan') == 3 and code.count('class="plan popular"') == 1
    assert "<strong>£395</strong>" in code and "<strong>£1,595.50</strong> <span>/month</span>" in code
    assert "<strong>Ask us</strong>" in code and 'href="/buy"' in code and 'href="#contact"' in code
    assert '<li class="no"><span class="sr">Not included: </span>Booking</li>' in code
    assert "Talk to us<span class=\"sr\"> for Custom</span>" in code and "Pay half to start." in code
    assert "<script" not in code and read(tmp_path, "pricing-preview.html").startswith("<!doctype html>")


def test_currency_and_no_popular(s, tmp_path):
    out = ask({"plans": [{"name": "Night", "price": 1200, "period": "night"}], "currency": "zar"}, s)
    assert "1 plan " in out and "Tip:" in out
    assert "<strong>R1,200</strong> <span>/night</span>" in read(tmp_path)


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours_pass_aa(brand):
    code = dp.block("X", brand, "T", "", [], "")
    get = lambda k: re.search(rf"--p-{k}:(#[0-9a-f]{{6}})", code).group(1)  # noqa: E731
    assert ratio(get("brand"), get("on")) >= AA and ratio(get("accent"), "#ffffff") >= AA


def test_escapes(s, tmp_path):
    ask({"plans": [{"name": "<b>X</b>", "price": "<i>9</i>", "features": ["<script>"]}], "title": "A & B"}, s)
    code = read(tmp_path)
    assert "<b>X" not in code and "<i>9" not in code and "<script>" not in code and "A &amp; B" in code


@pytest.mark.parametrize("args, words", [
    ({"name": "", "plans": PLANS}, "business name"),
    ({"plans": []}, "1 to 4"),
    ({"plans": PLANS * 2}, "1 to 4"),
    ({"plans": [{"name": "A"}]}, "needs a price"),
    ({"plans": [{"name": "A", "price": -5}]}, "0 or more"),
    ({"plans": [{"price": 5}]}, "needs a name"),
    ({"plans": [{"name": "A", "price": 5, "period": "fortnight"}]}, "Period can be"),
    ({"plans": [{"name": "A", "price": 5, "features": ["x"] * 11}]}, "10 features"),
    ({"plans": [{"name": "A", "price": 5, "popular": True}, {"name": "B", "price": 6, "popular": True}]}, "just one"),
    ({"plans": [{"name": "A", "price": 5, "link": "javascript:alert(1)"}]}, "isn't a link"),
    ({"plans": PLANS, "currency": "BTC"}, "Currency can be"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dp in tools.ABILITIES and [t["name"] for t in dp.tool_definitions()] == ["make_pricing_table"]
