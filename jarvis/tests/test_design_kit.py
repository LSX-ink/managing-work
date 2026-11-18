import asyncio

import pytest

import design_kit as dk
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dk.run_tool("make_brand_kit", args, settings))


def test_kit_writes_everything(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#c2410c", "heading_font": "Fraunces", "body_font": "Inter",
               "feel": "bouncy", "shape": "pill"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery"
    assert "style-guide.html" in out and "Fraunces headings" in out
    for f in ("palette.css", "palette.md", "type.css", "type.md", "motion.css", "motion.md", "tokens.css",
              "style-guide.html"):
        assert (folder / f).exists(), f
    assert "--radius-lg: 9999px" in (folder / "tokens.css").read_text()
    page = (folder / "style-guide.html").read_text()
    for link in ("palette.css", "type.css", "motion.css", "tokens.css"):
        assert f'href="{link}"' in page
    assert "Lebo&#x27;s Bakery" in page and "pop-in" in page and "#c2410c" in page


def test_name_is_escaped_in_page(s, tmp_path):
    ask({"name": "Tom & <Jerry>", "colour": "#2563eb"}, s)
    page = next((tmp_path / "Kinetic Web Designs").glob("*/style-guide.html")).read_text()
    assert "<Jerry>" not in page and "&amp;" in page


def test_bad_input(s):
    assert "Give the brand" in ask({"colour": "#2563eb"}, s)
    assert "Pick a shape" in ask({"name": "X", "colour": "#2563eb", "shape": "blob"}, s)
    assert "Can't read the colour" in ask({"name": "X", "colour": "teal-ish"}, s)


def test_registered():
    assert dk in tools.ABILITIES
