import asyncio

import pytest
from PIL import Image

import design_loyalty as dl
import tools
from config import Settings
from design_cards import BLEED, SIZE


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dl.run_tool("make_loyalty_card", args, settings))


def test_default_card(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#fde047", "item": "coffee"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "print"
    assert "10-stamp loyalty card" in out and "Your 10th coffee is free" in out
    for f in ("loyalty-front.png", "loyalty-back.png", "loyalty-preview.png"):
        assert (folder / f).exists()
    pdf = (folder / "loyalty.pdf").read_bytes()
    assert pdf.startswith(b"%PDF") and b"/Count 2" in pdf
    front = Image.open(folder / "loyalty-front.png")
    assert front.size == SIZE and front.getpixel((2, 2)) == (0xfd, 0xe0, 0x47)


def test_free_stamp_is_brand_coloured(s, tmp_path):
    ask({"name": "Fade Inn", "colour": "#111827", "stamps": 6, "reward": "Free cut after 5 visits",
         "name_line": False}, s)
    back = Image.open(tmp_path / "Kinetic Web Designs" / "Fade Inn" / "print" / "loyalty-back.png").convert("RGB")
    # one row of 6: the right-most circle's middle edge is filled with the brand colour
    row = [back.getpixel((x, SIZE[1] // 2 + 40)) for x in range(SIZE[0] - BLEED - 200, SIZE[0] - BLEED)]
    assert (0x11, 0x18, 0x27) in row


@pytest.mark.parametrize("n, cols_rows", [(4, (4, 1)), (6, (6, 1)), (7, (4, 2)), (10, (5, 2)), (12, (6, 2))])
def test_grid(n, cols_rows):
    assert dl.grid(n) == cols_rows


@pytest.mark.parametrize("n, word", [(1, "1st"), (2, "2nd"), (3, "3rd"), (8, "8th"), (11, "11th"), (12, "12th")])
def test_ordinal(n, word):
    assert dl.ordinal(n) == word


@pytest.mark.parametrize("stamps", [4, 7, 9, 12])
def test_every_size_draws(stamps):
    image, cuts = dl.back("#2563eb", stamps, "Free treat", True)
    assert image.size == SIZE and not cuts


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000"}, "business name"),
    ({"name": "X", "colour": "#000", "stamps": 3}, "between 4 and 12"),
    ({"name": "X", "colour": "#000", "stamps": 13}, "between 4 and 12"),
    ({"name": "X", "colour": "#000", "reward": "x" * 51}, "50 letters"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dl in tools.ABILITIES and [t["name"] for t in dl.tool_definitions()] == ["make_loyalty_card"]
