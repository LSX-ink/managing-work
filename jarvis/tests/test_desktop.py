import asyncio

import pytest

import browser
import desktop
import tools
from config import Settings


def tab(title, selected=False, window=0, where="Chrome", url=""):
    return {"title": title, "selected": selected, "window": window, "where": where, "url": url}


TABS = [tab("J.A.R.V.I.S.", selected=True), tab("Inbox (3) - alfredw.lsx@gmail.com - Gmail"),
        tab("Lo-fi beats - YouTube"), tab("Football highlights - YouTube"),
        tab("Amazon.co.uk: running shoes", selected=True, window=1), tab("BBC News - Home", window=1)]


def titles(chosen):
    return [t["title"] for t in chosen]


def test_registered_always_loaded():
    defs = {t["name"]: t for t in tools.client_tool_definitions(Settings())}
    for name in desktop.NAMES:
        assert name in defs and not defs[name].get("defer_loading")
    assert desktop in tools.ABILITIES


def test_said_words():
    assert desktop.said_words("the YouTube tab") == ["youtube"]
    assert desktop.said_words("you tube") == ["youtube"]
    assert desktop.said_words("my g mail tab") == ["gmail"]


def test_pick_by_name_and_misheard():
    assert titles(desktop.pick(TABS, "the YouTube tab")) == ["Lo-fi beats - YouTube", "Football highlights - YouTube"]
    assert titles(desktop.pick(TABS, "youtub")) == ["Lo-fi beats - YouTube", "Football highlights - YouTube"]
    assert titles(desktop.pick(TABS, "lo fi")) == ["Lo-fi beats - YouTube"]
    assert titles(desktop.pick(TABS, "amazon")) == ["Amazon.co.uk: running shoes"]
    assert desktop.pick(TABS, "netflix") == []


def test_this_tab_skips_alfreds_own_screen():
    assert titles(desktop.pick(TABS, "this")) == ["Amazon.co.uk: running shoes"]
    assert titles(desktop.pick(TABS, "")) == ["Amazon.co.uk: running shoes"]


def test_all_except():
    left = titles(desktop.pick(TABS, "all", keep=["Gmail"]))
    assert "J.A.R.V.I.S." not in left and not any("Gmail" in t for t in left) and len(left) == 4
    assert titles(desktop.pick(TABS, "all except gmail and bbc")) == [
        "Lo-fi beats - YouTube", "Football highlights - YouTube", "Amazon.co.uk: running shoes"]
    assert "J.A.R.V.I.S." not in titles(desktop.pick(TABS, "all"))


def test_alfred_screen_never_picked():
    assert desktop.is_alfred(tab("Alfred"))
    assert desktop.is_alfred(tab("anything", url="http://127.0.0.1:8340/"))
    assert not desktop.is_alfred(tab("Alfred Hitchcock - Wikipedia"))


def test_many_tabs_need_a_yes():
    assert desktop.needs_yes([1, 2, 3], "youtube")
    assert desktop.needs_yes([1, 2], "all")
    assert not desktop.needs_yes([1, 2], "youtube")
    assert not desktop.needs_yes([1], "all")


def test_safety_helpers():
    assert desktop.is_outward("Chat with Sam - WhatsApp")
    assert desktop.is_outward("Inbox - Outlook")
    assert not desktop.is_outward("Notepad")
    assert desktop.looks_like_card("4111 1111 1111 1111")
    assert not desktop.looks_like_card("lo-fi beats 2024")


def test_search_urls():
    assert desktop.search_url("YouTube", "lo-fi beats") == "https://www.youtube.com/results?search_query=lo-fi+beats"
    assert desktop.search_url("google.com", "a&b").endswith("q=a%26b")
    assert desktop.search_url("windows", "notepad") is None


def test_site_search_opens_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(desktop.webbrowser, "open", opened.append)
    out = asyncio.run(desktop.run_tool("screen_do", {"action": "search", "where": "youtube", "text": "lo-fi"}, Settings()))
    assert opened == ["https://www.youtube.com/results?search_query=lo-fi"] and "lo-fi" in out


def _job(monkeypatch, real, **kw):
    closed = []
    monkeypatch.setattr(desktop, "WINDOWS", True)
    monkeypatch.setattr(desktop, "_real_tabs", lambda: [dict(t) for t in real])
    monkeypatch.setattr(desktop, "_close_real", lambda t: closed.append(t["title"]))
    args = dict(action="close", target="", keep=[], which="any", confirmed=False, alfred_tabs=[])
    args.update(kw)
    reply, follow = desktop._tabs_job(**args)
    return reply, follow, closed


def test_close_one_tab(monkeypatch):
    reply, _, closed = _job(monkeypatch, TABS, target="BBC")
    assert closed == ["BBC News - Home"] and "Closed 1 tab" in reply


def test_close_many_reads_back_first(monkeypatch):
    reply, _, closed = _job(monkeypatch, TABS, target="all", keep=["gmail"])
    assert closed == [] and "would close 4 tabs" in reply and "confirmed" in reply
    reply, _, closed = _job(monkeypatch, TABS, target="all", keep=["gmail"], confirmed=True)
    assert len(closed) == 4 and "J.A.R.V.I.S." not in closed


def test_alfreds_browser_tabs_too(monkeypatch):
    mine = [{"id": 0, "title": "Weather - BBC", "url": "https://bbc.co.uk/weather", "selected": True}]
    reply, follow, closed = _job(monkeypatch, [], target="weather", alfred_tabs=mine)
    assert follow == ("close", [0]) and closed == [] and "Weather - BBC" in reply


def test_list_and_no_match(monkeypatch):
    reply, _, _ = _job(monkeypatch, TABS, action="list")
    assert "5 tabs open" in reply and "J.A.R.V.I.S." not in reply
    reply, _, _ = _job(monkeypatch, TABS, target="netflix")
    assert "can't see a tab" in reply


def test_alfred_browser_tabs_real(monkeypatch, tmp_path):
    pytest.importorskip("playwright")
    monkeypatch.setenv("JARVIS_BROWSER_HEADLESS", "true")
    settings = Settings()
    run = lambda **a: asyncio.run(browser.run_tool("web_browser", a, settings))
    try:
        try:
            run(action="open", url="example.invalid")  # the page won't load, but the tab opens
        except ValueError as exc:
            if "couldn't start a browser" in str(exc):
                pytest.skip("no browser on this machine")
        listed = asyncio.run(browser.tabs())
        assert len(listed) == 1
        assert asyncio.run(browser.close_tabs([0])) == 1
        assert asyncio.run(browser.tabs()) == []
    finally:
        run(action="close")
