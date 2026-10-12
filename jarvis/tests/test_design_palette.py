import asyncio

import pytest

import design_palette as dp
import tools
from config import Settings
from design_contrast import AA, ratio


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dp.run_tool("make_palette", args, settings))


@pytest.mark.parametrize("brand", ["#4f46e5", "#facc15", "#dc2626", "#0f766e", "#111111", "#f5f5f5"])
def test_roles_are_readable(brand):
    p = dp.build(brand)
    for mode in ("light", "dark"):
        r = p["roles"][mode]
        for role in ("text", "muted text", "link"):
            assert ratio(r[role], r["background"]) >= AA, (brand, mode, role)
        assert ratio(r["button text"], r["button"]) >= 3  # at least large-text/UI safe


def test_scale_runs_light_to_dark_and_keeps_hue():
    p = dp.build("#4f46e5")
    lights = [dp.hls(v)[1] for v in p["shades"].values()]
    assert lights == sorted(lights, reverse=True) and len(lights) == 11
    r, g, b = dp.rgb(p["shades"][500])
    assert b > r > g or b > g  # still indigo/blue


def test_harmonies():
    assert len(dp.build("#ff0000", "triadic")["accents"]) == 2
    assert dp.build("#ff0000", "mono")["accents"] == []
    comp = dp.build("#ff0000")["accents"][0]["hex"]
    assert comp == "#00ffff"
    with pytest.raises(ValueError):
        dp.build("#ff0000", "rainbow")


def test_summary_and_save(s, tmp_path):
    out = ask({"colour": "#4f46e5"}, s)
    assert "Palette from #4f46e5" in out and "Light page" in out and "Saved" not in out
    out = ask({"colour": "rgb(220, 38, 38)", "harmony": "analogous", "name": "Lebo's Bakery"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery"
    assert "Saved palette.md and palette.css" in out
    assert "--brand-500" in (folder / "palette.css").read_text() and "prefers-color-scheme: dark" in (
        folder / "palette.css").read_text()
    assert "## Dark page" in (folder / "palette.md").read_text()


def test_bad_colour(s):
    assert "Can't read the colour" in ask({"colour": "blurple"}, s)


def test_registered():
    assert dp in tools.ABILITIES
