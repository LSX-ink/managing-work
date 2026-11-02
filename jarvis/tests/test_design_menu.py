import asyncio

import pytest
from PIL import Image

import design_menu as dm
import tools
from config import Settings
from design_contrast import AA, ratio

CUTS = {"title": "Cuts", "items": [{"name": "Skin fade", "price": "£18", "note": "Includes wash and style"},
                                   {"name": "Scissor cut", "price": "£20"}, {"name": "Kids", "price": "£12"}]}


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dm.run_tool("make_price_list", args, settings))


def test_a4_list(s, tmp_path):
    out = ask({"name": "Fade Inn", "colour": "#111827", "sections": [CUTS], "footer": "Book at fadeinn.co.uk"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Fade Inn" / "print"
    assert "A4 price list" in out and "3 items in 1 section" in out
    page = Image.open(folder / "price-list.png")
    w, h = round(210 * dm.MM) + 2 * dm.BLEED, round(297 * dm.MM) + 2 * dm.BLEED
    assert page.size == (w, h) and round(page.info["dpi"][0]) == 300
    assert page.getpixel((5, 5)) == (0x11, 0x18, 0x27)  # header runs into the bleed
    assert page.getpixel((5, h - 5)) == (255, 255, 255)
    assert (folder / "price-list.pdf").read_bytes().startswith(b"%PDF")


def test_a5_light_brand_and_two_columns(s, tmp_path):
    many = [{"title": f"Part {n}", "items": [{"name": f"Item {n}-{i}", "price": f"£{i}"} for i in range(6)]}
            for n in range(5)]
    out = ask({"name": "Sunny Café", "colour": "#fde047", "sections": many, "paper": "a5", "title": "Menu"}, s)
    assert "A5 price list" in out and "30 items in 5 sections" in out
    page = Image.open(tmp_path / "Kinetic Web Designs" / "Sunny Café" / "print" / "menu.png")
    assert page.size[0] == round(148 * dm.MM) + 2 * dm.BLEED


def test_columns_keep_titles_with_items():
    parts = dm.blocks(dm.items_of([CUTS, dict(CUTS, title="Beard"), dict(CUTS, title="Extras")]), 1.0)
    first, second = dm.columns(parts, 2)
    assert first[-1][0] == "item" and second[0][0] != "gap"  # no title left alone at the bottom
    assert sum(p[2] for p in first) + sum(p[2] for p in second) <= sum(p[2] for p in parts)


def test_light_brand_prices_still_read():
    assert ratio("#fde047", "#ffffff") < AA  # yellow on white is too faint, so prices use a deeper shade


def test_too_long_and_bad_input(s):
    huge = [{"title": "All", "items": [{"name": "Thing with a long name " * 2, "price": "£1", "note": "note"}] * 80}]
    assert "doesn't fit on one A5 page" in ask({"name": "A", "colour": "#000", "sections": huge, "paper": "A5"}, s)
    assert "split it into two lists" in ask({"name": "A", "colour": "#000", "sections": [{"items": [
        {"name": "x", "price": "1"}] * 81}]}, s)
    assert "Give the business name" in ask({"colour": "#000", "sections": [CUTS]}, s)
    assert "Give the sections" in ask({"name": "A", "colour": "#000"}, s)
    assert "needs a name" in ask({"name": "A", "colour": "#000", "sections": [{"items": [{"price": "£1"}]}]}, s)
    assert "at least one item" in ask({"name": "A", "colour": "#000", "sections": [{"title": "X", "items": []}]}, s)
    assert "A4 or A5" in ask({"name": "A", "colour": "#000", "sections": [CUTS], "paper": "A3"}, s)


def test_registered():
    assert dm in tools.ABILITIES
