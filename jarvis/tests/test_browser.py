import asyncio
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

import browser
import tools
from config import Settings

PAGE = """<html><head><title>Test shop</title></head><body>
<h1>Welcome to the test shop</h1>
<a href="/second.html">More news</a>
<input name="q" placeholder="Search">
<input type="password" name="pw" placeholder="Password">
<button>Buy now</button>
</body></html>"""
SECOND = "<html><head><title>Second page</title></head><body><p>The second page says hello.</p></body></html>"


@pytest.fixture
def settings():
    return Settings()


def test_registered_and_deferred(settings):
    defs = [t for t in tools.client_tool_definitions(settings) if t["name"] == "web_browser"]
    assert len(defs) == 1 and defs[0].get("defer_loading")
    assert browser in tools.ABILITIES


def test_normalise_url():
    assert browser.normalise_url("bbc.co.uk") == "https://bbc.co.uk"
    assert browser.normalise_url("http://example.com/a") == "http://example.com/a"
    assert browser.normalise_url("localhost:8000") == "https://localhost:8000"
    for bad in ("", "file:///C:/secret.txt", "javascript:alert(1)", "data:text/html,hi"):
        with pytest.raises(ValueError):
            browser.normalise_url(bad)


def test_never_types_secrets():
    assert browser.is_secret({"type": "password", "label": "", "name": ""})
    assert browser.is_secret({"type": "text", "auto": "cc-number", "label": "", "name": ""})
    assert browser.is_secret({"type": "text", "label": "Card number", "name": ""})
    assert browser.is_secret({"type": "tel", "label": "", "name": "cvv cvv"})
    assert not browser.is_secret({"type": "search", "label": "Search", "name": "q"})


def test_risky_clicks_need_a_yes():
    assert browser.is_risky("Buy now")
    assert browser.is_risky("Place order")
    assert browser.is_risky("Delete account")
    assert not browser.is_risky("More news")
    assert not browser.is_risky("Paypal help")  # whole words only
    assert not browser.is_risky("Repost history")


def test_find_item_by_number_and_text():
    items = [{"id": 1, "kind": "link", "label": "More news"}, {"id": 2, "kind": "box", "label": "Search"},
             {"id": 3, "kind": "button", "label": "Buy now"}]
    assert browser.find_item(items, "3")["label"] == "Buy now"
    assert browser.find_item(items, "more")["id"] == 1
    assert browser.find_item(items, "", boxes=True)["id"] == 2
    with pytest.raises(ValueError):
        browser.find_item(items, "9")
    with pytest.raises(ValueError):
        browser.find_item(items, "weather")
    with pytest.raises(ValueError):
        browser.find_item([], "1")


def test_unknown_action_and_closed_browser(settings):
    with pytest.raises(ValueError):
        asyncio.run(browser.run_tool("web_browser", {"action": "fly"}, settings))
    with pytest.raises(ValueError, match="isn't open"):
        asyncio.run(browser.run_tool("web_browser", {"action": "read"}, settings))
    assert asyncio.run(browser.run_tool("web_browser", {"action": "close"}, settings)) == "Closed the browser."


@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text(PAGE)
    (tmp_path / "second.html").write_text(SECOND)
    server = HTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/index.html"
    server.shutdown()


def test_drives_a_real_page(settings, site, monkeypatch):
    pytest.importorskip("playwright")
    monkeypatch.setenv("JARVIS_BROWSER_HEADLESS", "true")
    run = lambda **a: asyncio.run(browser.run_tool("web_browser", a, settings))
    try:
        try:
            page = run(action="open", url=site)
        except ValueError as exc:
            if "couldn't start a browser" in str(exc):
                pytest.skip("no browser on this machine")
            raise
        assert "Test shop" in page and "Welcome to the test shop" in page and "] link: More news" in page
        assert "never type" in run(action="type", target="Password", text="hunter2")
        assert "Typed into Search" in run(action="type", target="Search", text="shoes")
        assert "confirm" in run(action="click", target="Buy now")
        after = run(action="click", target="More news")
        assert "Second page" in after and "says hello" in after
        assert "Test shop" in run(action="back")
        shot = run(action="screenshot")
        assert shot[0]["type"] == "image" and shot[0]["source"]["media_type"] == "image/jpeg"
    finally:
        run(action="close")
