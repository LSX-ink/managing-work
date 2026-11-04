import asyncio
import csv
import datetime as dt
import re

import pytest
from PIL import Image

import design_voucher as dv
import tools
from config import Settings

TODAY = dt.date(2026, 11, 4)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    try:
        return dv.run(settings, args, today=TODAY)
    except (TypeError, ValueError) as e:
        return str(e)


def test_batch_of_vouchers(s, tmp_path):
    out = ask({"name": "Fade Inn", "colour": "#111827", "value": "£25", "count": 3, "prefix": "fade!",
               "website": "fadeinn.co.uk"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Fade Inn" / "print"
    assert "Made 3 gift vouchers" in out and "valid until 4 Nov 2027" in out and "QR code" in out
    pdf = (folder / "vouchers-2026-11-04.pdf").read_bytes()
    assert pdf.startswith(b"%PDF") and len(re.findall(rb"/Type\s*/Page\b", pdf)) == 3  # one page each
    rows = list(csv.DictReader(open(folder / "vouchers-2026-11-04.csv", encoding="utf-8")))
    assert [r["valid until"] for r in rows] == ["2027-11-04"] * 3 and all(r["used"] == "" for r in rows)
    found = [r["code"] for r in rows]
    assert len(set(found)) == 3
    assert all(re.fullmatch(r"FADE-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}", c) for c in found)
    preview = Image.open(folder / "vouchers-2026-11-04-preview.png")
    assert preview.size == (dv.TRIM[0] // 2, dv.TRIM[1] // 2)
    assert preview.getpixel((10, 10)) == (0x11, 0x18, 0x27) and preview.getpixel((preview.width - 10, 10)) == \
        (255, 255, 255)


def test_second_batch_never_overwrites(s, tmp_path):
    ask({"name": "Fade Inn", "colour": "#111827", "value": "£10"}, s)
    out = ask({"name": "Fade Inn", "colour": "#111827", "value": "One free haircut", "to": "Sam"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Fade Inn" / "print"
    assert "vouchers-2026-11-04-2.pdf" in out
    assert (folder / "vouchers-2026-11-04.csv").exists() and (folder / "vouchers-2026-11-04-2.csv").exists()


def test_page_size_and_bleed():
    page, cuts = dv.draw("#fde047", "Lebo's Bakery", "£25", "", "ABCD-EFGH", dt.date(2027, 1, 1), "", None)
    assert page.size == (dv.TRIM[0] + 2 * dv.BLEED, dv.TRIM[1] + 2 * dv.BLEED) and not cuts
    assert page.getpixel((2, 2)) == (0xfd, 0xe0, 0x47)  # brand panel runs into the bleed


@pytest.mark.parametrize("args, expected", [
    ({"months": 1}, dt.date(2026, 12, 4)),
    ({"months": 24}, dt.date(2028, 11, 4)),
    ({"expires": "2027-03-01"}, dt.date(2027, 3, 1)),
])
def test_expiry(args, expected):
    assert dv.expiry(args, TODAY) == expected


def test_expiry_month_end():
    assert dv.expiry({"months": 3}, dt.date(2026, 11, 30)) == dt.date(2027, 2, 28)
    assert dv.expiry({"months": 1}, dt.date(2026, 12, 31)) == dt.date(2027, 1, 31)


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000", "value": "£5"}, "business name"),
    ({"name": "X", "colour": "#000"}, "worth"),
    ({"name": "X", "colour": "#000", "value": "x" * 41}, "40 letters"),
    ({"name": "X", "colour": "#000", "value": "£5", "count": 51}, "between 1 and 50"),
    ({"name": "X", "colour": "#000", "value": "£5", "expires": "2026-11-01"}, "after today"),
    ({"name": "X", "colour": "#000", "value": "£5", "expires": "next year"}, "like 2027"),
    ({"name": "X", "colour": "#000", "value": "£5", "months": 99}, "between 1 and 60"),
    ({"name": "X", "colour": "#000", "value": "£5", "website": "javascript:alert(1)"}, "isn't a web address"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_run_tool_and_registered(s):
    out = asyncio.run(dv.run_tool("make_gift_voucher", {"name": "X", "colour": "#000000"}, s))
    assert "worth" in out
    assert dv in tools.ABILITIES and [t["name"] for t in dv.tool_definitions()] == ["make_gift_voucher"]
