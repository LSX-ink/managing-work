import asyncio

import pytest
from PIL import Image

import design_sign as dsg
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dsg.run_tool("make_qr_sign", args, settings))


def test_review_sign_a5(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#fde047", "link": "g.page/r/Cabc123/review",
               "headline": "Loved it? Leave us a review", "text": "It takes 30 seconds", "title": "Review sign"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "print"
    assert "Made an A5 QR sign" in out and "opens g.page/r/Cabc123/review" in out
    page = Image.open(folder / "review-sign.png")
    assert page.size == (round(148 * dsg.MM) + 2 * dsg.BLEED, round(210 * dsg.MM) + 2 * dsg.BLEED)
    assert page.getpixel((3, 3)) == (0xfd, 0xe0, 0x47)  # header runs into the bleed
    assert (folder / "review-sign.pdf").read_bytes().startswith(b"%PDF")
    # the QR's dark squares sit in the middle of the page
    mid = page.crop((page.width // 3, page.height // 3, 2 * page.width // 3, 2 * page.height // 3)).convert("L")
    assert mid.getextrema()[0] == 0


def test_phone_and_wifi(s, tmp_path):
    out = ask({"name": "Fade Inn", "colour": "#111827", "phone": "0121 496 0000", "paper": "a4"}, s)
    assert "Made an A4 QR sign" in out and "calls 0121 496 0000" in out
    out = ask({"name": "Fade Inn", "colour": "#111827", "wifi_name": "Fade Guest", "wifi_password": "cuts2026"}, s)
    assert "joins the Wi-Fi" in out and "guest network" in out
    assert (tmp_path / "Kinetic Web Designs" / "Fade Inn" / "print" / "wifi-sign.png").exists()


def test_kind_and_qr_text():
    assert dsg.target({"link": "https://www.fadeinn.co.uk/book"})[1:] == ("https://www.fadeinn.co.uk/book",
                                                                         "fadeinn.co.uk/book")
    assert dsg.target({"phone": "+44 121 496 0000"})[1] == "tel:+441214960000"
    assert dsg.wifi_text('My;Net', 'p"a:ss\\', "WPA") == r'WIFI:T:WPA;S:My\;Net;P:p\"a\:ss\\;;'
    assert dsg.wifi_text("Open Cafe", "", "none") == "WIFI:T:nopass;S:Open Cafe;;"


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000", "link": "a.com"}, "business name"),
    ({"name": "X", "colour": "#000"}, "Give the link"),
    ({"name": "X", "colour": "#000", "link": "javascript:alert(1)"}, "isn't a web address"),
    ({"name": "X", "colour": "#000", "kind": "phone", "phone": "12"}, "phone number"),
    ({"name": "X", "colour": "#000", "kind": "wifi", "wifi_name": "N"}, "password"),
    ({"name": "X", "colour": "#000", "kind": "wifi", "wifi_name": "N", "wifi_password": "p",
      "wifi_security": "wpa9"}, "wpa (most routers)"),
    ({"name": "X", "colour": "#000", "kind": "fax"}, "link, phone or wifi"),
    ({"name": "X", "colour": "#000", "link": "a.com", "headline": "x" * 61}, "60 letters"),
    ({"name": "X", "colour": "#000", "link": "a.com", "paper": "A3"}, "A4 or A5"),
    ({"name": "X", "colour": "#000", "link": "a.com/" + "x" * 3000}, "too long"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dsg in tools.ABILITIES and [t["name"] for t in dsg.tool_definitions()] == ["make_qr_sign"]
