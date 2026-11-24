import asyncio
import re

import pytest

import design_services as ds
import tools
from config import Settings
from design_contrast import AA, UI, ratio

SVC = [{"title": "Wedding cakes", "text": "Tiered cakes.", "price": 350, "url": "/weddings"},
       {"title": "Bread delivery", "text": "At your door.", "price": "£4.50 a loaf"},
       {"title": "Baking classes", "text": "Learn sourdough.", "icon": "star"}]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(ds.run_tool("make_services_section", {"name": "Lebo's Bakery", "colour": "#c2410c",
                                                             "services": SVC, **args}, settings))


def read(tmp_path, file="services.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_full_section(s, tmp_path):
    out = ask({"intro": "Baked daily.", "button": "Order now", "link": "/order"}, s)
    assert "3 services" in out and "Wedding cakes = cake" in out and "Baking classes = star" in out
    code = read(tmp_path)
    assert code.count('<li class="sv-card">') == 3 and "<h3>Wedding cakes</h3>" in code
    assert "From £350" in code and "£4.50 a loaf" in code and code.count("<svg") == 3
    assert '<a class="sv-more" href="/weddings">Learn more<span class="sv-sr"> about Wedding cakes</span>' in code
    assert code.count("sv-more\" href") == 1 and '<p class="sv-cta"><a href="/order">Order now</a></p>' in code
    assert "<script" not in code and "prefers-reduced-motion" in code
    assert read(tmp_path, "services-preview.html").startswith("<!doctype html>")


def test_numbers_and_tips(s, tmp_path):
    five = [{"title": f"Service {i}", "text": "Words."} for i in range(5)]
    out = ask({"services": five, "style": "numbers"}, s)
    assert "gap on the last row" in out and "Add a button" in out and "Icons:" not in out
    code = read(tmp_path)
    assert '<span class="sv-num">01</span>' in code and '<span class="sv-num">05</span>' in code and "<svg" not in code


@pytest.mark.parametrize("title, icon", [("Skin fade", "scissors"), ("Same day delivery", "truck"),
                                         ("Garden design", "leaf"), ("Roof repairs", "home"), ("Something", "check"),
                                         ("Car valeting", "sparkle"), ("Sourdough workshop", "book")])
def test_guess(title, icon):
    assert ds.guess(title) == icon


def test_prices():
    assert ds.price_text(45, "GBP") == "From £45" and ds.price_text(12.5, "ZAR") == "From R12.50"
    assert ds.price_text(None, "GBP") == "" and ds.price_text("POA", "GBP") == "POA"
    assert ds.price_text(1200, "USD") == "From $1,200"


@pytest.mark.parametrize("bad, msg", [
    ({"services": SVC[:1]}, "2 to 9"),
    ({"services": [{"title": "A"}, {"title": "B", "text": "x"}]}, "needs a name"),
    ({"services": [{"title": "A", "text": "x", "url": "javascript:x"}, SVC[0]]}, "isn't one I can use"),
    ({"services": [{"title": "A", "text": "x", "icon": "rocket"}, SVC[0]]}, "Icons can be"),
    ({"services": [{"title": "A", "text": "x"}, {"title": "a", "text": "y"}]}, "same name"),
    ({"services": [{"title": "A", "text": "x" * 300}, SVC[0]]}, "under 260"),
    ({"services": [{"title": "A", "text": "x", "price": -1}, SVC[0]]}, "below zero"),
    ({"currency": "JPY"}, "Currency can be"),
])
def test_rejects(s, bad, msg):
    out = ask(bad, s)
    assert msg in out and "Made a services" not in out


def test_escapes(s, tmp_path):
    ask({"services": [{"title": "<b>A</b>", "text": "<i>x</i>"}, SVC[1]]}, s)
    code = read(tmp_path)
    assert "&lt;b&gt;A&lt;/b&gt;" in code and "<i>x" not in code


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours(brand):
    code = ds.block({"name": "X", "brand": brand, "services": [{"title": "A", "text": "x", "icon": "check",
                     "url": "", "price": ""}] * 2, "numbers": False, "title": "T", "intro": "", "button": "",
                     "link": ""})
    get = lambda k: re.search(rf"--sv-{k}:(#[0-9a-f]{{6}})", code).group(1)  # noqa: E731
    assert ratio(get("brand"), get("on")) >= AA and ratio(get("accent"), "#ffffff") >= AA
    assert ratio(get("icon"), get("tint")) >= UI


def test_registered():
    assert ds in tools.ABILITIES and [t["name"] for t in ds.tool_definitions()] == ["make_services_section"]
