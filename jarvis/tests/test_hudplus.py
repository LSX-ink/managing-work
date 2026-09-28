import asyncio
import json

import httpx
import pytest

import hudplus
import screen
import tools
from config import Settings


def call(args, settings=None):
    """The tool through tools.run_tool; the reply is a Shown when a card reached the page, else plain text."""
    sent = []

    def refuse(request):
        raise AssertionError(f"Unexpected request to {request.url}")

    async def page(msg):
        sent.append(msg)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(refuse)) as http:
            return await tools.run_tool("hud_control", args, settings or Settings(), http, page)

    text = asyncio.run(go())
    if not sent:
        return text
    assert sent[0]["type"] == "popup"
    return screen.Shown(text, sent[0]["card"])


def data(shown):
    assert isinstance(shown, screen.Shown)
    assert shown.card["kind"] == "hud" and shown.card["id"] == "hud-control"
    return shown.card["data"]


def test_tool_is_registered_and_deferred():
    names = [t["name"] for t in tools.client_tool_definitions(Settings())]
    assert names.count("hud_control") == 1
    assert next(t for t in tools.client_tool_definitions(Settings()) if t["name"] == "hud_control")["defer_loading"]
    schema = hudplus.tool_definitions()[0]["input_schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]["action"]["enum"]) == set(hudplus.ACTIONS)


@pytest.mark.parametrize("action, expected", [
    ("tidy_windows", "tidy"), ("close_windows", "close_all"), ("minimise_windows", "minimise_all"),
    ("shortcuts", "shortcuts"), ("palette", "palette"),
])
def test_window_actions(action, expected):
    assert data(call({"action": action}))["action"] == expected


def test_focus_and_clean_screen():
    assert data(call({"action": "focus_mode", "on": True})) == {"action": "focus", "on": True}
    toggled = call({"action": "focus_mode"})
    assert data(toggled) == {"action": "focus", "on": None} and "Toggled" in toggled
    assert data(call({"action": "clean_screen", "on": False})) == {"action": "clean", "on": False}
    assert call({"action": "clean_screen", "on": True}) == "Side panels hidden."


def test_screensaver():
    assert data(call({"action": "screensaver", "on": True}))["on"] is True
    assert data(call({"action": "screensaver", "on": False}))["on"] is False
    shown = call({"action": "screensaver", "minutes": 500})
    assert data(shown)["minutes"] == 120 and "120 idle minutes" in shown


def test_theme_and_zoom():
    assert data(call({"action": "theme", "theme": "hud-gold"}))["theme"] == "hud-gold"
    assert data(call({"action": "theme"}))["theme"] == "toggle"
    with pytest.raises(ValueError):
        call({"action": "theme", "theme": "pink"})
    assert data(call({"action": "zoom", "zoom": "smaller"}))["zoom"] == "smaller"
    assert call({"action": "zoom", "zoom": "reset"}) == "Back to normal size."
    with pytest.raises(ValueError):
        call({"action": "zoom", "zoom": "huge"})


def test_help_is_a_clickable_list():
    shown = call({"action": "help"})
    assert shown.card["kind"] == "list"
    assert len(shown.card["items"]) == 20
    assert all(item["say"] for item in shown.card["items"])


def test_sticky_notes(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    added = call({"action": "note_add", "text": "  Buy   milk ", "colour": "pink"}, s)
    note = data(added)["note"]
    assert note["text"] == "Buy milk" and note["colour"] == "pink"
    call({"action": "note_add", "text": "Ring Mum", "colour": "purple"}, s)
    saved = json.loads((tmp_path / "sticky-notes.json").read_text())["notes"]
    assert [n["text"] for n in saved] == ["Buy milk", "Ring Mum"] and saved[1]["colour"] == "yellow"
    with pytest.raises(ValueError):
        call({"action": "note_add", "text": "  "}, s)

    listed = call({"action": "note_list"}, s)
    assert data(listed)["action"] == "notes_show" and "Buy milk; Ring Mum" in listed

    asked = call({"action": "note_remove", "text": "milk"}, s)
    assert not isinstance(asked, screen.Shown) and "confirm" in asked
    assert len(hudplus.load_notes(s)) == 2
    removed = call({"action": "note_remove", "text": "MILK", "confirmed": True}, s)
    assert data(removed) == {"action": "note_remove", "match": "milk"}
    assert [n["text"] for n in hudplus.load_notes(s)] == ["Ring Mum"]

    assert "confirm" in call({"action": "note_clear"}, s)
    assert data(call({"action": "note_clear", "confirmed": True}, s))["action"] == "note_clear"
    assert hudplus.load_notes(s) == []
    assert "haven't added" in call({"action": "note_list"}, s)


def test_notes_file_limits(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    (tmp_path / "sticky-notes.json").write_text("not json")
    assert hudplus.load_notes(s) == []
    hudplus.save_notes(s, [{"id": str(i), "text": "x"} for i in range(hudplus.MAX_NOTES)])
    with pytest.raises(ValueError):
        call({"action": "note_add", "text": "one more"}, s)


def test_unknown_action():
    with pytest.raises(ValueError):
        call({"action": "explode"})
