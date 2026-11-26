import asyncio
import re

import pytest

import design_stats as dsb
import tools
from config import Settings
from design_contrast import AA, ratio

STATS = [{"value": "15", "label": "years in Hockley"}, {"value": "2,000+", "label": "cakes made"},
         {"value": "4.9★", "label": "on Google"}]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dsb.run_tool("make_stats_band", {"name": "Lebo's Bakery", "colour": "#c2410c",
                                                        "stats": STATS, **args}, settings))


def read(tmp_path, file="stats.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_band(s, tmp_path):
    out = ask({"title": "Since 2011", "source": "Google, May 2026"}, s)
    assert "3 numbers" in out and "CAP code" in out and "Add a source" not in out
    code = read(tmp_path)
    assert 'aria-labelledby="sb-title"' in code and '<h2 class="sb-title" id="sb-title">Since 2011</h2>' in code
    assert code.count('<li class="sb-item">') == 3 and "<strong>2,000+</strong> <span>cakes made</span>" in code
    assert "repeat(3, minmax(0, 1fr))" in code and '<p class="sb-source">Google, May 2026</p>' in code
    assert "<script" not in code and "prefers-reduced-motion" in code
    assert read(tmp_path, "stats-preview.html").startswith("<!doctype html>")


def test_light_no_title(s, tmp_path):
    out = ask({"style": "light", "stats": STATS[:2]}, s)
    assert "Add a source" in out
    code = read(tmp_path)
    assert 'aria-label="Lebo&#x27;s Bakery in numbers"' in code and "sb-title\"" not in code.split("</style>")[1]
    assert "sb-source\">" not in code


@pytest.mark.parametrize("bad, msg", [
    ({"stats": STATS[:1]}, "2 to 4"),
    ({"stats": STATS * 2}, "2 to 4"),
    ({"stats": [{"value": "15"}, STATS[0]]}, "needs the number"),
    ({"stats": [{"value": "lots", "label": "x"}, STATS[0]]}, "has no number"),
    ({"stats": [{"value": "123456789012", "label": "x"}, STATS[0]]}, "under 10"),
    ({"stats": [{"value": "1", "label": "x" * 50}, STATS[0]]}, "under 40"),
    ({"style": "neon"}, "Style can be"),
])
def test_rejects(s, bad, msg):
    out = ask(bad, s)
    assert msg in out and "Made a" not in out


def test_escapes(s, tmp_path):
    ask({"stats": [{"value": "<b>1</b>", "label": "<i>x</i>"}, STATS[0]]}, s)
    code = read(tmp_path)
    assert "&lt;b&gt;1&lt;/b&gt;" in code and "<i>x" not in code


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
@pytest.mark.parametrize("style", ["band", "light"])
def test_colours(brand, style):
    c = dsb.colours(brand, style)
    assert all(ratio(c[k], c["bg"]) >= AA for k in ("num", "label", "soft"))
    code = dsb.block({"name": "X", "brand": brand, "style": style, "stats": STATS, "title": "", "source": ""})
    assert re.search(r"--sb-bg:#[0-9a-f]{6}", code)


def test_registered():
    assert dsb in tools.ABILITIES and [t["name"] for t in dsb.tool_definitions()] == ["make_stats_band"]
