import asyncio
import math

import pytest
from PIL import Image

import design_highlights as dh
import tools
from config import Settings
from design_contrast import UI, ratio


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dh.run_tool("make_highlight_covers", args, settings))


def folder(tmp_path, name):
    return tmp_path / "Kinetic Web Designs" / name / "posts" / "highlights"


def test_makes_numbered_covers_and_preview(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#c2410c",
               "highlights": ["Prices", "Reviews", {"label": "Find us"}, {"label": "Team", "text": "lb"}]}, s)
    assert "Made 4 solid highlight covers" in out and "first letter" not in out
    files = sorted(p.name for p in folder(tmp_path, "Lebo's Bakery").iterdir())
    assert files == ["01-prices.png", "02-reviews.png", "03-find-us.png", "04-team.png", "highlights-preview.png"]
    assert Image.open(folder(tmp_path, "Lebo's Bakery") / "01-prices.png").size == dh.SIZE


def test_rerun_removes_old_covers(s, tmp_path):
    ask({"name": "Shop", "colour": "#333333", "highlights": ["Shop", "Reviews", "Hours"]}, s)
    ask({"name": "Shop", "colour": "#333333", "highlights": ["Hours"]}, s)
    assert sorted(p.name for p in folder(tmp_path, "Shop").glob("[0-9]*.png")) == ["01-hours.png"]


@pytest.mark.parametrize("label, kind", [("Reviews", "star"), ("Opening hours", "clock"), ("Find us", "pin"),
                                         ("Our menu", "menu"), ("FAQ", "chat"), ("Prices", "tag"),
                                         ("Haircuts", "scissors"), ("Book now", "calendar"), ("Gallery", "camera")])
def test_guesses_icons(label, kind):
    assert dh.guess(label) == kind


def test_unknown_label_uses_first_letter_and_says_so(s):
    assert "No icon matched 'Zebra'" in ask({"name": "Z", "colour": "#333333", "highlights": ["Zebra"]}, s)


@pytest.mark.parametrize("style", dh.STYLES)
@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f"])
def test_icon_inside_circle_and_readable(style, brand):
    for kind in dh.ICONS:
        image = dh.cover(brand, style, kind, "")
        back = image.getpixel((5, 5))
        cx, cy = dh.SIZE[0] / 2, dh.SIZE[1] / 2
        px = image.load()
        marks, far = 0, 0
        for y in range(0, dh.SIZE[1], 6):
            for x in range(0, dh.SIZE[0], 6):
                if px[x, y] != back:
                    marks += 1
                    far = max(far, math.hypot(x - cx, y - cy))
        assert marks > 50, kind
        assert far <= dh.CIRCLE / 2 + 12, (kind, far)
        colours = {c for _, c in image.getcolors(1 << 20)} - {back}
        ink = max(colours, key=lambda c: sum(abs(a - b) for a, b in zip(c, back)))
        assert ratio("#%02x%02x%02x" % ink, "#%02x%02x%02x" % back) >= UI, kind


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000", "highlights": ["a"]}, "business name"),
    ({"name": "X", "colour": "#000", "highlights": []}, "1 to 12"),
    ({"name": "X", "colour": "#000", "highlights": ["a"] * 13}, "1 to 12"),
    ({"name": "X", "colour": "#000", "highlights": ["a"], "style": "glitter"}, "Pick a style"),
    ({"name": "X", "colour": "#000", "highlights": [{"label": "a", "icon": "rocket"}]}, "Icons can be"),
    ({"name": "X", "colour": "#000", "highlights": [{"label": "a", "text": "ABCD"}]}, "1 to 3 letters"),
    ({"name": "X", "colour": "#000", "highlights": [{"label": " "}]}, "needs a label"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dh in tools.ABILITIES and [t["name"] for t in dh.tool_definitions()] == ["make_highlight_covers"]
