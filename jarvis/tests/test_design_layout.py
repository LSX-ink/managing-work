import asyncio

import pytest

import design_layout as dl
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dl.run_tool("make_layout", args, settings))


def test_build_defaults():
    layout = dl.build()
    assert layout["columns"] == {"phone": 4, "tablet": 8, "desktop": 12}
    assert layout["gutter"]["css"].startswith("clamp(1rem,") and layout["gutter"]["css"].endswith("2rem)")
    assert [s["name"] for s in layout["space"]][0] == "3xs" and len(layout["space"]) == 9
    assert 50 < layout["column_width"] < 80


def test_density_gets_airier():
    compact, spacious = dl.build("compact"), dl.build("spacious")
    assert compact["gutter"]["desktop"] < spacious["gutter"]["desktop"]
    assert compact["space"][-1]["desktop"] < spacious["space"][-1]["desktop"]


def test_small_column_counts_keep_tablet_sane():
    assert dl.build(columns=6)["columns"]["tablet"] == 6


def test_css_has_grid_and_spans():
    text = dl.css(dl.build(columns=12))
    assert "--columns: 12" in text and "--columns: 8" in text and "--columns: 4" in text
    assert ".lg\\:span-12 { grid-column: span 12; }" in text and ".md\\:span-8" in text and ".md\\:span-9" not in text
    assert "auto-fill, minmax(min(100%, 280px), 1fr)" in text and "--space-3xl: clamp(" in text


def test_summary_and_save(s, tmp_path):
    out = ask({}, s)
    assert "Layout grid (comfortable)" in out and "Saved" not in out
    out = ask({"name": "Lebo's Bakery", "density": "spacious", "columns": 12}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery"
    assert "Saved layout.md" in out
    page = (folder / "layout-preview.html").read_text()
    assert 'href="layout.css"' in page and "lg:span-6" in page and "Card 6" in page
    assert "| 3xl |" in (folder / "layout.md").read_text()


def test_bad_input(s):
    assert "Pick a density" in ask({"density": "roomy"}, s)
    assert "between 4 and 16" in ask({"columns": 30}, s)
    assert "container width" in ask({"max_width": 300}, s)


def test_registered():
    assert dl in tools.ABILITIES
