import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import tools
import tts


def test_read_open_tasks_keeps_only_unchecked(tmp_path):
    note = tmp_path / "Tasks.md"
    note.write_text("# Tasks\n- [ ] Call mum\n- [x] Done thing\n  * [ ] Nested item\n- [ ]\nNot a task\n", encoding="utf-8")
    assert tools.read_open_tasks(str(note)) == ["Call mum", "Nested item"]


def test_read_open_tasks_missing_file_is_empty(tmp_path):
    assert tools.read_open_tasks(str(tmp_path / "nope.md")) == []


@pytest.mark.parametrize(
    "url, ok",
    [
        ("https://example.com/page", True),
        ("http://localhost:8000", True),
        ("file:///etc/passwd", False),
        ("javascript:alert(1)", False),
        ("example.com", False),
    ],
)
def test_is_safe_url(url, ok):
    assert tools.is_safe_url(url) is ok


async def test_open_url_refuses_non_http():
    assert (await tools.open_url("file:///etc/passwd")).startswith("Refused")


def test_split_sentences_respects_limit():
    text = "One. Two is longer. Three!"
    assert tts.split_sentences(text, limit=12) == ["One.", "Two is longer.", "Three!"]
    assert tts.split_sentences(text) == [text]


def test_websocket_rejects_other_origins(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    import server

    with TestClient(server.app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws", headers={"origin": "https://evil.example"}) as ws:
                ws.receive_json()
        with client.websocket_connect("/ws", headers={"origin": "http://testserver"}):
            pass
        assert client.get("/config").json()["speechLang"]


@pytest.mark.parametrize(
    "lang, override, expected",
    [
        ("en-GB", "", "eleven_turbo_v2_5"),
        ("af-ZA", "", "eleven_v3"),
        ("af-ZA", "eleven_multilingual_v2", "eleven_multilingual_v2"),
    ],
)
def test_elevenlabs_model_follows_language(lang, override, expected):
    from config import Settings

    assert tts.elevenlabs_model(Settings(speech_lang=lang, elevenlabs_model=override)) == expected
