import asyncio

import pytest

import design_footer as df
import tools
from config import Settings
from design_contrast import AA, ratio


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


COLS = [{"title": "Visit", "links": [{"text": "Menu", "url": "/menu"}, {"text": "Order", "url": "https://order.x"}]},
        {"title": "Company", "links": [{"text": "About", "url": "/about"}]}]


def ask(args, settings):
    return asyncio.run(df.run_tool("make_site_footer", {"name": "Lebo's Bakery", "colour": "#c2410c", **args},
                                   settings))


def read(tmp_path, file="footer.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_full_footer(s, tmp_path):
    out = ask({"tagline": "Sourdough in Hockley", "columns": COLS, "country": "GB", "phone": "0121 496 0000",
               "email": "hi@lebo.co.uk", "address": ["21 Hockley Hill", "B18 5BW"], "hours": "Mon-Sat 8-4",
               "socials": {"instagram": "@lebo"}, "terms_url": "/terms", "year": 2026, "legal_name": "Lebo Ltd",
               "company_line": "Registered in England No. 12345678"}, s)
    assert "2 link columns" in out and "company_line" not in out
    code = read(tmp_path)
    assert '<nav class="f-col" aria-labelledby="f-c0">' in code and '<h2 id="f-c0">Visit</h2>' in code
    assert '<a href="/menu">Menu</a>' in code and 'href="https://order.x" target="_blank" rel="noopener"' in code
    assert 'href="tel:+441214960000"' in code and 'href="mailto:hi@lebo.co.uk"' in code
    assert "21 Hockley Hill<br>B18 5BW" in code and "https://instagram.com/lebo" in code
    assert "© 2026 Lebo Ltd. Registered in England No. 12345678" in code
    assert '<a href="/privacy">Privacy</a><a href="/terms">Terms</a>' in code and "ck-open" in code
    assert 'href="#top"' in code and "<script" not in code
    assert 'id="top"' in read(tmp_path, "footer-preview.html")


def test_minimal_and_tips(s, tmp_path):
    out = ask({"country": "GB", "cookie_button": False, "back_to_top": False}, s)
    assert "0 link columns" in out and "Add a phone" in out and "company_line" in out
    code = read(tmp_path)
    assert "Cookie settings" not in code and "#top" not in code and "Get in touch" not in code


@pytest.mark.parametrize("bad, msg", [
    ({"columns": [{"title": "X", "links": [{"text": "a", "url": "javascript:alert(1)"}]}]}, "isn't one I can use"),
    ({"columns": [{"title": "X", "links": []}]}, "1 to 8 links"),
    ({"columns": [{"links": [{"text": "a", "url": "/a"}]}]}, "needs a title"),
    ({"columns": COLS * 3}, "up to 4"),
    ({"email": "nope"}, "email"),
    ({"socials": {"myspace": "x"}}, "Socials can be"),
    ({"year": "soon"}, "copyright year"),
    ({"colour": ""}, ""),
])
def test_rejects(s, bad, msg):
    out = ask(bad, s)
    assert msg in out and "Made a footer" not in out


def test_escapes(s, tmp_path):
    ask({"tagline": "<b>hi</b>", "columns": [{"title": "<i>", "links": [{"text": "<x>", "url": "/a"}]}]}, s)
    code = read(tmp_path)
    assert "&lt;b&gt;hi&lt;/b&gt;" in code and "<i>" not in code and "&lt;x&gt;" in code


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e", "#1d4ed8"])
def test_colours(brand):
    c = df.shades(brand)
    assert ratio(c["text"], c["bg"]) >= AA and ratio(c["soft"], c["bg"]) >= AA and ratio(c["link"], c["bg"]) >= AA


def test_registered():
    assert df in tools.ABILITIES and [t["name"] for t in df.tool_definitions()] == ["make_site_footer"]
