import asyncio
import xml.etree.ElementTree as ET

import pytest

import design_logo as dl
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dl.run_tool("make_logo", args, settings))


@pytest.mark.parametrize("name,want", [("Lebo's Bakery", "LB"), ("Kinetic", "KI"), ("The Bread & Butter Co", "BB"),
                                      ("Q", "Q"), ("7 Eleven", "7E")])
def test_initials(name, want):
    assert dl.initials(name) == want


def test_given_initials_win():
    assert dl.initials("Lebo's Bakery", "lb!") == "LB"


def test_makes_valid_svgs(s, tmp_path):
    out = ask({"name": "Tom & Jerry's", "colour": "#facc15"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Tom & Jerry's" / "logo"
    assert "Made 5 starter logo files" in out and "favicon.svg" in out
    for f in ("logo-tile.svg", "logo-badge.svg", "logo-outline.svg", "logo-wordmark.svg", "logo-wordmark-dark.svg",
              "favicon.svg"):
        root = ET.fromstring((folder / f).read_text())  # well-formed even with & and ' in the name
        assert root.tag.endswith("svg")
    tile = (folder / "logo-tile.svg").read_text()
    assert "#facc15" in tile and 'fill="#0b0b0f"' in tile  # dark initials on yellow
    assert 'width="64"' in (folder / "favicon.svg").read_text()
    page = (folder / "logos.html").read_text()
    assert "Tom &amp; Jerry" in page
    light, dark = page.split('class="dark"')
    assert "logo-wordmark-dark.svg" not in light and 'src="logo-wordmark.svg"' not in dark
    assert 'fill="#ffffff">Tom &amp; Jerry' in (folder / "logo-wordmark-dark.svg").read_text()


def test_light_text_on_dark_brand(s, tmp_path):
    ask({"name": "Night Owl", "colour": "#1e1b4b", "styles": ["badge"]}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Night Owl" / "logo"
    assert 'fill="#ffffff"' in (folder / "logo-badge.svg").read_text()
    assert not (folder / "logo-tile.svg").exists()


def test_bad_input(s):
    assert "Give the brand" in ask({"colour": "#000"}, s)
    assert "Can't read the colour" in ask({"name": "X", "colour": "bluish"}, s)
    assert "at least one letter" in ask({"name": "!!!", "colour": "#000"}, s)


def test_registered():
    assert dl in tools.ABILITIES
