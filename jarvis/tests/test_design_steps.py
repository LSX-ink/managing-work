import asyncio
import re

import pytest

import design_steps as dst
import tools
from config import Settings
from design_contrast import AA, UI, ratio

STEPS = [{"title": "Book online", "text": "Pick a time.", "time": "Takes 2 minutes"},
         {"title": "We visit", "text": "Fixed price quote."},
         {"title": "Job done", "text": "Pay when happy."}]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dst.run_tool("make_steps_section", {"name": "Lebo's Bakery", "colour": "#c2410c",
                                                           "steps": STEPS, **args}, settings))


def read(tmp_path, file="steps.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_full_section(s, tmp_path):
    out = ask({"intro": "Simple.", "note": "No call-out fee.", "button": "Book now", "link": "/book"}, s)
    assert "3 steps" in out and "timeline on a phone" in out and "Add a button" not in out
    code = read(tmp_path)
    assert '<ol class="st-list" role="list">' in code and code.count('<li class="st-step">') == 3
    assert '<span class="st-dot" aria-hidden="true">1</span>' in code and "<h3>Job done</h3>" in code
    assert '<p class="st-when">Takes 2 minutes</p>' in code and code.count("st-when\">") == 1
    assert "No call-out fee." in code and '<p class="st-cta"><a href="/book">Book now</a></p>' in code
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in code and "max-width: 44rem" in code
    assert ".st-step:nth-child(3) { animation-delay: 0.24s; }" in code and "{{" not in code
    assert "<script" not in code and read(tmp_path, "steps-preview.html").startswith("<!doctype html>")


def test_defaults_and_tips(s, tmp_path):
    many = [{"title": f"Step {i}", "text": "Words."} for i in range(6)]
    out = ask({"steps": many}, s)
    assert "6 steps is a lot" in out and "Add a button" in out
    code = read(tmp_path)
    assert ">How it works<" in code and "st-cta" not in code.split("</style>")[1] and "max-width: 72rem" in code


@pytest.mark.parametrize("bad, msg", [
    ({"steps": STEPS[:1]}, "2 to 6"),
    ({"steps": STEPS * 3}, "2 to 6"),
    ({"steps": [{"title": "A"}, STEPS[0]]}, "needs a short title"),
    ({"steps": [{"title": "A" * 50, "text": "x"}, STEPS[0]]}, "under 40"),
    ({"steps": [{"title": "A", "text": "x" * 250}, STEPS[0]]}, "under 200"),
    ({"button": "Go", "link": "javascript:x"}, "isn't one I can use"),
])
def test_rejects(s, bad, msg):
    out = ask(bad, s)
    assert msg in out and "Made a" not in out


def test_escapes(s, tmp_path):
    ask({"steps": [{"title": "<b>A</b>", "text": "<i>x</i>"}, STEPS[1]]}, s)
    code = read(tmp_path)
    assert "&lt;b&gt;A&lt;/b&gt;" in code and "<i>x" not in code


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours(brand):
    code = dst.block({"name": "X", "brand": brand, "steps": [{"title": "A", "text": "x", "time": ""}] * 2,
                      "title": "T", "intro": "", "note": "", "button": "", "link": ""})
    get = lambda k: re.search(rf"--st-{k}:(#[0-9a-f]{{6}})", code).group(1)  # noqa: E731
    assert ratio(get("brand"), get("on")) >= AA and ratio(get("accent"), "#ffffff") >= AA
    assert ratio(get("line"), "#ffffff") >= UI


def test_registered():
    assert dst in tools.ABILITIES and [t["name"] for t in dst.tool_definitions()] == ["make_steps_section"]
