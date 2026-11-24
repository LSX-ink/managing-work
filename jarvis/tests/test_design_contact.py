import asyncio
import json
import re

import pytest

import design_contact as dc
import tools
from config import Settings
from design_contrast import AA, ratio

FULL = {"country": "GB", "phone": "0121 496 0000", "whatsapp": "07700 900123", "email": "hi@lebos.co.uk",
        "address": ["21 Hockley Hill", "Birmingham", "B18 5BW"], "hours": "Mon-Sat 7am-4pm",
        "socials": {"instagram": "@lebosbakery", "Facebook": "lebos"}}


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dc.run_tool("make_contact_section", {"name": "Lebo's Bakery", "colour": "#c2410c", **args},
                                   settings))


def read(tmp_path, file="contact.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_full_section(s, tmp_path):
    out = ask(FULL, s)
    assert "one-tap call, WhatsApp, email, directions" in out
    code = read(tmp_path)
    assert 'href="tel:+441214960000"' in code and 'href="https://wa.me/447700900123"' in code
    assert 'href="mailto:hi@lebos.co.uk"' in code
    assert "google.com/maps/search/?api=1&amp;query=Lebo%27s%20Bakery%2C%2021%20Hockley%20Hill" in code
    assert "<br>Birmingham<br>B18 5BW</address>" in code and "Mon-Sat 7am-4pm" in code
    assert code.count('class="c-btn main"') == 1 and "iframe" not in code and "<script>" not in code
    data = json.loads(re.search(r'ld\+json">\s*(.*?)\s*</script>', code, re.S).group(1))
    assert data["telephone"] == "+441214960000" and data["address"]["addressCountry"] == "GB"
    assert data["address"]["streetAddress"] == "21 Hockley Hill, Birmingham, B18 5BW"
    assert data["sameAs"] == ["https://instagram.com/lebosbakery", "https://facebook.com/lebos"]
    assert read(tmp_path, "contact-preview.html").startswith("<!doctype html>")


def test_email_only_and_address_text(s, tmp_path):
    ask({"email": "hi@lebos.co.uk", "address": "1 High St, Leeds"}, s)
    code = read(tmp_path)
    assert 'class="c-btn main" href="mailto:hi@lebos.co.uk"' in code and "tel:" not in code
    assert "1 High St<br>Leeds" in code


@pytest.mark.parametrize("phone, country, link", [("0121 496 0000", "GB", "+441214960000"),
                                                  ("+27 21 555 0100", "", "+27215550100"),
                                                  ("0027 21 555 0100", "", "+27215550100"),
                                                  ("021 555 0100", "ZA", "+27215550100"),
                                                  ("0121 496 0000", "", "01214960000")])
def test_phone_links(phone, country, link):
    assert dc.phone_link(phone, country) == link


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours(s, tmp_path, brand):
    asyncio.run(dc.run_tool("make_contact_section", {"name": "Shop", "colour": brand, "email": "a@b.co"}, s))
    code = (tmp_path / "Kinetic Web Designs" / "Shop" / "web" / "contact.html").read_text(encoding="utf-8")
    get = lambda k: re.search(rf"--c-{k}:(#[0-9a-f]{{6}})", code).group(1)  # noqa: E731
    assert ratio(get("brand"), get("on")) >= AA and ratio(get("accent"), "#ffffff") >= AA


def test_escapes(s, tmp_path):
    ask({"email": "a@b.co", "address": ["<b>1</b> St"], "intro": "<script>x</script>", "title": "A & B"}, s)
    code = read(tmp_path).split("ld+json")[0]
    assert "<b>1" not in code and "<script>x" not in code and "A &amp; B" in code


@pytest.mark.parametrize("args, words", [
    ({"name": "", "email": "a@b.co"}, "business name"),
    ({}, "at least one way"),
    ({"email": "nope"}, "email"),
    ({"phone": "12"}, "too short"),
    ({"whatsapp": "07700 900123"}, "country code"),
    ({"phone": "0121 496 0000", "country": "XX"}, "Country can be"),
    ({"email": "a@b.co", "socials": {"myspace": "a"}}, "Socials can be"),
    ({"email": "a@b.co", "socials": {"instagram": "bad handle!"}}, "handle"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dc in tools.ABILITIES and [t["name"] for t in dc.tool_definitions()] == ["make_contact_section"]
