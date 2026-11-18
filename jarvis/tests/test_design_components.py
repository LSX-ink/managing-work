import asyncio

import pytest

import design_components as dc
import tools
from config import Settings
from design_contrast import ratio

UI_CHECKS = {"Text box border", "Focus ring", "Focus ring (dark)"}


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dc.run_tool("make_components", args, settings))


@pytest.mark.parametrize("brand", ["#c2410c", "#facc15", "#1e1b4b", "#22c55e", "#000000", "#ffffff", "#0ea5e9"])
def test_every_pair_passes(brand):
    kit = dc.build(brand)
    for name, value in kit["checks"].items():
        assert value >= (3 if name in UI_CHECKS else 4.5), (brand, name, value)
    c = kit["colours"]
    assert ratio(c["primary-text"], c["primary-pressed"]) >= 4.5


def test_hover_moves_the_right_way():
    white = dc.build("#c2410c")["colours"]
    assert white["primary-text"] == "#ffffff" and white["primary-hover"] != white["primary"]
    assert ratio("#ffffff", white["primary-hover"]) > ratio("#ffffff", white["primary"])  # deeper under white words
    ink = dc.build("#facc15")["colours"]
    assert ink["primary-text"] == "#0b0b0f" and ratio("#0b0b0f", ink["primary-hover"]) > ratio("#0b0b0f", "#facc15")


def test_shapes():
    assert dc.build("#c2410c", "pill")["radii"][0] == 9999
    assert "--radius-button: 4px" in dc.css(dc.build("#c2410c", "sharp"))
    with pytest.raises(ValueError):
        dc.build("#c2410c", "blob")


def test_summary_and_save(s, tmp_path):
    out = ask({"colour": "#c2410c"}, s)
    assert "primary button #c2410c" in out and "Saved" not in out
    out = ask({"colour": "#c2410c", "name": "Tom & <Jerry>", "shape": "pill"}, s)
    folder = next((tmp_path / "Kinetic Web Designs").iterdir())
    css = (folder / "components.css").read_text()
    assert "--c-primary: #c2410c;" in css and ".btn:focus-visible" in css and "prefers-reduced-motion" in css
    page = (folder / "components.html").read_text()
    assert 'href="components.css"' in page and "<Jerry>" not in page and "disabled>Disabled" in page
    assert "Saved components.css" in out


def test_bad_input(s):
    assert "Can't read the colour" in ask({"colour": "orangey"}, s)
    assert "Pick a shape" in ask({"colour": "#000", "shape": "blob"}, s)


def test_registered():
    assert dc in tools.ABILITIES
