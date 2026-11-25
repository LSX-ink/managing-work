import asyncio
import sys
import types

import quickpc
from config import Settings


def test_scroll_commands():
    assert quickpc.command("scroll down") == {"scroll": "down", "amount": 1.0, "say": "Scrolled down."}
    assert quickpc.command("Alfred, scroll up please.")["scroll"] == "up"
    assert quickpc.command("scroll down a bit")["amount"] == 0.4
    assert quickpc.command("scroll down a lot")["amount"] == 3.0
    assert quickpc.command("scroll down three times")["amount"] == 3.0
    assert quickpc.command("scroll")["scroll"] == "down"
    assert quickpc.command("can you scroll down")["scroll"] == "down"


def test_key_commands():
    assert quickpc.command("next tab")["keys"] == "ctrl+tab"
    assert quickpc.command("close this tab")["keys"] == "ctrl+w"
    assert quickpc.command("go back")["keys"] == "alt+left"
    assert quickpc.command("press enter")["keys"] == "enter"
    assert quickpc.command("refresh the page")["keys"] == "f5"
    assert quickpc.command("go to the top")["keys"] == "home"
    assert quickpc.command("zoom in")["keys"] == "ctrl+="


def test_everything_else_goes_to_the_ai():
    for said in ("scroll down and click the second link", "close the YouTube tab", "what's the time",
                 "go back to what you were saying", "undo that", "top", "[activate]", "", "tell me about tabs"):
        assert quickpc.command(said) is None, said


def test_not_on_windows_does_nothing(monkeypatch):
    monkeypatch.setattr(quickpc, "WINDOWS", False)
    assert asyncio.run(quickpc.handle("scroll down", Settings())) is None


def _fake(monkeypatch, title):
    pressed, wheel = [], []
    import desktop
    monkeypatch.setattr(desktop, "_front", lambda window="": (1, title))
    monkeypatch.setattr(desktop, "_keys", pressed.append)
    monkeypatch.setattr(desktop, "_auto", lambda: (_ for _ in ()).throw(RuntimeError("no UIA")))
    gui = types.SimpleNamespace(scroll=wheel.append, hscroll=wheel.append, moveTo=lambda *a: None)
    monkeypatch.setitem(sys.modules, "pyautogui", gui)
    return pressed, wheel


def test_does_it(monkeypatch):
    pressed, wheel = _fake(monkeypatch, "Football - YouTube - Google Chrome")
    assert quickpc._do(quickpc.command("next tab")) == "Next tab."
    assert quickpc._do(quickpc.command("scroll down")) == "Scrolled down."
    assert pressed == ["ctrl+tab"] and wheel == [-600]


def test_hands_over_when_unsure(monkeypatch):
    pressed, _ = _fake(monkeypatch, "Notepad")
    assert quickpc._do(quickpc.command("go back")) is None  # no browser in front
    pressed, _ = _fake(monkeypatch, "Chat with Sam - WhatsApp")
    assert quickpc._do(quickpc.command("press enter")) is None  # could send a message: the AI asks
    assert pressed == []


def test_open_and_search_commands():
    assert quickpc.command("open Spotify") == {"open": "spotify", "query": ""}
    assert quickpc.command("open Spotify and search Drake") == {"open": "spotify", "query": "drake"}
    assert quickpc.command("search YouTube for lo-fi beats") == {"open": "youtube", "query": "lo-fi beats"}
    assert quickpc.command("search lo-fi on youtube") == {"open": "youtube", "query": "lo-fi"}
    assert quickpc.command("google best pizza") == {"open": "google", "query": "best pizza"}
    assert quickpc.command("search Windows for notepad") == {"windows": "notepad"}
    assert quickpc.command("open file explorer")["open"] == "file explorer"
    for said in ("open the youtube tab", "open my emails", "open it", "open the first result"):
        assert quickpc.command(said) is None, said


def _fake_pc(monkeypatch, windows=(), apps=()):
    import desktop
    import pc
    calls = []
    monkeypatch.setattr(desktop, "_all_windows", lambda: list(windows))
    monkeypatch.setattr(desktop, "_bring", lambda w: calls.append(("bring", w["title"])))
    monkeypatch.setattr(pc, "installed_apps", lambda: list(apps))
    monkeypatch.setattr(pc, "open_app", lambda n: calls.append(("app", n)) or f"Opened {n}.")
    monkeypatch.setattr(pc, "open_folder", lambda n: calls.append(("folder", n)) or "Opened.")
    monkeypatch.setattr(quickpc, "_search_app", lambda n, q: calls.append(("search", n, q)) or "Searching.")
    import webbrowser
    monkeypatch.setattr(webbrowser, "open", lambda u: calls.append(("web", u)))
    return calls


def test_open_uses_what_is_on_the_pc(monkeypatch):
    calls = _fake_pc(monkeypatch, windows=[{"hwnd": 1, "title": "Spotify Premium", "exe": "spotify"}])
    assert quickpc._do({"open": "spotify", "query": ""}) == "Here's spotify."
    assert calls == [("bring", "Spotify Premium")]
    calls = _fake_pc(monkeypatch, apps=[("Spotify", "Spotify.ID")])
    assert quickpc._do({"open": "spotify", "query": "drake"}) == "Searching."
    assert calls == [("app", "Spotify"), ("search", "Spotify", "drake")]
    calls = _fake_pc(monkeypatch)
    quickpc._do({"open": "youtube", "query": "lo-fi"})
    assert calls == [("web", "https://www.youtube.com/results?search_query=lo-fi")]
    calls = _fake_pc(monkeypatch)
    quickpc._do({"open": "downloads", "query": ""})
    assert calls == [("folder", "downloads")]
    calls = _fake_pc(monkeypatch)
    assert quickpc._do({"open": "zorblax", "query": ""}) is None and calls == []  # not on the PC: the AI takes it
