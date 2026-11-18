import asyncio
import re

import pytest

import design_type as dt
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dt.run_tool("make_type_scale", args, settings))


def test_scale_grows_and_phone_is_gentler():
    scale = dt.build(16, "perfect-fourth")
    assert scale["mobile_ratio"] == dt.RATIOS["major-third"]
    desktop = [x["desktop"] for x in scale["steps"]]
    assert desktop == sorted(desktop)
    base = next(x for x in scale["steps"] if x["name"] == "base")
    assert base["phone"] == base["desktop"] == 16 and base["size"] == "1rem"
    h1 = scale["steps"][-1]
    assert h1["phone"] < h1["desktop"] and h1["desktop"] == round(16 * 1.333 ** 6, 1)
    small = [x for x in scale["steps"] if x["step"] < 0]
    assert all(x["phone"] == x["desktop"] >= 12 for x in small)  # small print never shrinks on desktop


def test_clamp_hits_both_ends():
    small, large = 24, 48
    m = re.match(r"clamp\(([\d.]+)rem, ([-\d.]+)rem \+ ([\d.]+)vw, ([\d.]+)rem\)", dt.clamp(small, large))
    lo, intercept, vw, hi = (float(g) for g in m.groups())
    assert lo * 16 == small and hi * 16 == large
    for width, want in ((dt.MIN_VW, small), (dt.MAX_VW, large)):
        assert abs(intercept * 16 + vw / 100 * width - want) < 0.05


def test_ratio_choices():
    assert dt.ratio_value("Golden") == 1.618 and dt.ratio_value("1.2") == 1.2 and dt.ratio_value(1.5) == 1.5
    with pytest.raises(ValueError):
        dt.ratio_value("huge")
    with pytest.raises(ValueError):
        dt.ratio_value(3)
    assert dt.build(16, "minor-second")["mobile_ratio"] == 1.067  # nothing gentler, stays the same


def test_summary_and_save(s, tmp_path):
    out = ask({}, s)
    assert "ratio 1.25 on desktop" in out and "5xl" in out and "Saved" not in out
    out = ask({"ratio": "perfect-fifth", "heading_font": "Space Grotesk", "body_font": "Inter", "name": "Lebo's Bakery"},
              s)
    assert "Saved type.md and type.css" in out and "family=Space+Grotesk" in out
    css = (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "type.css").read_text()
    assert "--text-5xl: clamp(" in css and "h1 { font-size: var(--text-5xl)" in css and "@import url(" in css
    assert "| 5xl |" in (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "type.md").read_text()


def test_bad_input(s):
    assert "between 12 and 24" in ask({"base": 40}, s)
    assert "Pick a ratio" in ask({"ratio": "spicy"}, s)


def test_registered():
    assert dt in tools.ABILITIES
