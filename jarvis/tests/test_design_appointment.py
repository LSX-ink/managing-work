import asyncio

import pytest
from PIL import Image

import design_appointment as da
import tools
from config import Settings
from design_cards import SIZE


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(da.run_tool("make_appointment_card", args, settings))


def test_card_files(s, tmp_path):
    out = ask({"name": "Fade Inn", "colour": "#b91c1c", "phone": "0121 496 0000", "with_who": True}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Fade Inn" / "print"
    assert "2 write-in rows (day, date, time and who with)" in out
    for f in ("appointment-front.png", "appointment-back.png", "appointment-preview.png"):
        assert (folder / f).exists()
    pdf = (folder / "appointment.pdf").read_bytes()
    assert pdf.startswith(b"%PDF") and b"/Count 2" in pdf
    front = Image.open(folder / "appointment-front.png")
    assert front.size == SIZE and front.getpixel((2, 2)) == (0xb9, 0x1c, 0x1c)


def count_rows(image):
    """Write-in lines: grey rows that run across at least a fifth of the card."""
    rows, last = 0, -10
    for y in range(image.height):
        grey = sum(1 for x in range(0, image.width, 4) if image.getpixel((x, y)) == da.LINE)
        if grey > image.width / 20 and y > last + 5:
            rows += 1
        if grey > image.width / 20:
            last = y
    return rows


@pytest.mark.parametrize("rows", [1, 2, 3])
def test_rows_drawn(rows):
    image, cuts = da.back("#2563eb", rows, False, "Please give 24 hours' notice to cancel.", "0121 496 0000")
    assert count_rows(image.convert("RGB")) == rows and not cuts


def test_no_note(s, tmp_path):
    out = ask({"name": "Tutor", "colour": "#2563eb", "rows": 1, "note": "none"}, s)
    assert "1 write-in row " in out


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000"}, "business name"),
    ({"name": "X", "colour": "#000", "rows": 4}, "1 to 3"),
    ({"name": "X", "colour": "#000", "rows": 0}, "1 to 3"),
    ({"name": "X", "colour": "#000", "note": "x" * 71}, "70 letters"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert da in tools.ABILITIES and [t["name"] for t in da.tool_definitions()] == ["make_appointment_card"]
