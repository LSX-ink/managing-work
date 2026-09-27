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
        config = client.get("/config").json()
        assert config["speechLang"] and config["name"]


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


def test_websocket_confirmation_round_trip(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    import server

    class FakeBrain:
        def __init__(self, settings, client, http, confirm, page=None):
            self.confirm = confirm

        async def handle(self, text, speak):
            await speak("answer: " + await self.confirm(["Left click at (1, 2)"]))

    monkeypatch.setattr(server, "Brain", FakeBrain)
    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "alerts"  # the notifications list comes first
            ws.send_json({"text": "click"})
            ask = ws.receive_json()
            assert ask["type"] == "confirm" and ask["steps"] == ["Left click at (1, 2)"]
            ws.send_json({"type": "confirm_reply", "id": ask["id"], "answer": "allow"})
            assert ws.receive_json()["text"] == "answer: allow"
            assert ws.receive_json()["type"] == "done"


def test_config_reports_theme_and_weather_endpoint(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    from dataclasses import replace

    import server

    async def fake_weather(http, city):
        return f"{city}: 18°C"

    monkeypatch.setattr(server, "settings", replace(server.settings, theme="hud-gold", city="Johannesburg"))
    monkeypatch.setattr(server.tools, "get_weather", fake_weather)
    monkeypatch.setattr(server, "_weather", {"at": 0.0, "text": ""})
    with TestClient(server.app) as client:
        assert client.get("/config").json()["theme"] == "hud-gold"
        assert client.get("/weather").json() == {"text": "Johannesburg: 18°C"}


def test_password_locks_page_config_and_websocket(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    from dataclasses import replace

    import server

    monkeypatch.setattr(server, "settings", replace(server.settings, password="open sesame"))
    with TestClient(server.app) as client:
        page = client.get("/")
        assert page.status_code == 200 and 'name="password"' in page.text
        assert client.get("/config").status_code == 401
        assert client.get("/static/main.js").status_code == 401
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws") as ws:
                ws.receive_json()

        wrong = client.post("/login", data={"password": "nope"})
        assert wrong.status_code == 401 and "Wrong password" in wrong.text
        assert server.SESSION_COOKIE not in client.cookies

        ok = client.post("/login", data={"password": "open sesame"}, follow_redirects=False)
        assert ok.status_code == 303
        assert client.get("/config").status_code == 200
        assert 'name="password"' not in client.get("/").text
        with client.websocket_connect("/ws"):
            pass


def test_weather_forecast_for_coming_days():
    import asyncio

    import httpx
    import tools

    def handler(request):
        if "geocoding" in request.url.host:
            return httpx.Response(200, json={"results": [{"name": "Leeds", "country": "UK", "latitude": 1, "longitude": 2}]})
        assert request.url.params["forecast_days"] == "2"
        return httpx.Response(200, json={
            "current": {"temperature_2m": 12, "apparent_temperature": 10, "weather_code": 3, "wind_speed_10m": 9},
            "daily": {"time": ["2026-09-27", "2026-09-28"], "weather_code": [3, 61], "temperature_2m_max": [14, 11],
                      "temperature_2m_min": [7, 6], "precipitation_probability_max": [10, 80]},
        })

    async def main():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await tools.get_weather(http, "Leeds", 2)
    text = asyncio.run(main())
    assert text.endswith("Monday: " + tools.WEATHER_CODES[61] + ", high 11°C, low 6°C, 80% chance of rain.")


def test_inbox_text(monkeypatch):
    from datetime import datetime, timedelta

    import alerts
    import tools
    from config import Settings

    now = datetime.now().astimezone()
    mails = [alerts.Mail(1, "Old <o@x>", "Ancient", now - timedelta(hours=30)),
             alerts.Mail(2, "VGC <p@vgc>", "Your payslip", now - timedelta(hours=2)),
             alerts.Mail(3, "Mum <m@x>", "", now - timedelta(minutes=5))]
    monkeypatch.setattr(alerts, "fetch_mail", lambda settings, days, limit: mails)
    text = tools.inbox_text(Settings(), 24)
    assert text.startswith("2 emails in the last 24 hours")
    assert text.index("Mum") < text.index("VGC") and "(no subject)" in text and "Ancient" not in text


def test_listen_for_name_tells_the_page():
    import asyncio

    import tools
    from config import Settings

    sent = []

    async def page(message):
        sent.append(message)
    assert "only answering" in asyncio.run(tools.run_tool("listen_for_name", {"on": True}, Settings(), None, page))
    assert sent == [{"type": "wakeword", "on": True}]
