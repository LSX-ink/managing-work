import asyncio

import httpx
import pytest

import design_audit as da
import memory
import tools
from config import Settings

GOOD = """<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Lebo's Bakery | Fresh bread</title>
<meta name="description" content="Sourdough baked every morning in Croydon.">
<meta property="og:image" content="https://lebos.co.uk/share-home.png"><link rel="icon" href="favicon.svg">
<style>body { color: #111827; background: #ffffff; font-family: Inter, sans-serif; }</style></head>
<body><h1>Fresh bread</h1><h2>Order</h2><img src="a.jpg" alt="A loaf" width="400" height="300">
<a href="/order">Order today</a><button aria-label="Open menu"><svg></svg></button>
<label for="email">Email</label><input id="email" type="email"><label>Name <input type="text"></label>
<input type="submit" value="Send"></body></html>"""

BAD = """<html><head><style>
.hero { color: #9ca3af; background: #ffffff; } .fine { font-size: 10px; } .bg { color: #fff; background: transparent; }
a { font-family: 'Playfair Display'; } p { font-family: Lato; } h3 { font-family: Oswald, serif; }
small { font-family: "Roboto Mono"; }
</style></head><body><h1>A</h1><h1>B</h1><h4>C</h4><img src="x.png">
<a href="/x"><img src="i.png" alt=""></a><a href="/y">Click here</a><a href="https://z.com" target="_blank">Z</a>
<input type="text" placeholder="Name"><p style="color:#777;background-color:#888">grey</p></body></html>"""


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def test_good_page_scores_100():
    found = da.audit(GOOD)
    assert found["score"] == 100 and not found["fix"] and not found["tips"], found


def test_bad_page_lists_problems():
    found = da.audit(BAD)
    text = "\n".join(found["fix"] + found["tips"])
    for bit in ("language", "viewport", "<title>", "meta description", "1 picture has no alt", "1 link or button",
                "1 form box without a label", ".hero (#9ca3af on #ffffff", "#777777 on #888888", "Text under 12px",
                "2 H1", "H1 to H4", '"Click here"', "4 different fonts", 'rel="noopener"', "og:image", "favicon"):
        assert bit in text, bit
    assert ".bg" not in text  # see-through backgrounds aren't judged
    assert found["score"] < 40


def test_reads_a_memory_file(s, tmp_path):
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery"
    folder.mkdir(parents=True)
    (folder / "index.html").write_text(GOOD)
    out = asyncio.run(da.run_tool("audit_website", {"folder": "Kinetic Web Designs/Lebo's Bakery"}, s))
    assert "Kinetic Web Designs/Lebo's Bakery/index.html: 100/100" in out and "Nothing to fix" in out


def test_reads_a_link(s, monkeypatch):
    async def ok(url):
        return None
    monkeypatch.setattr(memory, "check_public", ok)

    def handler(request):
        return httpx.Response(200, text=BAD, headers={"content-type": "text/html"})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await da.run_tool("audit_website", {"url": "lebos.co.uk"}, s, http)
    out = asyncio.run(go())
    assert "https://lebos.co.uk" in out and "Fix:" in out and "Nice to have:" in out


def test_bad_input(s):
    assert "Give a website link" in asyncio.run(da.run_tool("audit_website", {}, s))
    assert "doesn't look like a website" in asyncio.run(da.run_tool("audit_website", {"url": "not a site"}, s))


def test_registered():
    assert da in tools.ABILITIES
