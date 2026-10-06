"""Security, a failed turn never leaving the page deaf, and the voice starting after the first sentence."""

from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient

import tts
from config import Settings


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    import server

    server._login_fails.clear()
    return server


@pytest.mark.parametrize("host, ok", [
    ("localhost:8340", True), ("127.0.0.1:8340", True), ("[::1]:8340", True), ("192.168.1.20:8340", True),
    ("my-pc.tail1234.ts.net", True), ("DESKTOP-ABC", True), ("testserver", True), (None, True),
    ("evil.example.com", False), ("rebind.attacker.net:8340", False),
])
def test_only_this_pc_and_the_phone_link_are_answered(server, host, ok):
    assert server.allowed_host(host) is ok


def test_an_unknown_web_address_is_refused(server, monkeypatch):
    client = TestClient(server.app)
    assert client.get("/config", headers={"host": "rebind.attacker.net"}).status_code == 421
    monkeypatch.setattr(server, "settings", replace(server.settings, allowed_hosts=("rebind.attacker.net",)))
    assert client.get("/config", headers={"host": "rebind.attacker.net"}).status_code == 200


def test_pages_cannot_be_shown_inside_other_sites(server, monkeypatch):
    monkeypatch.setattr(server, "settings", replace(server.settings, password="open sesame"))
    page = TestClient(server.app).get("/")  # the login page too
    assert page.headers["x-frame-options"] == "SAMEORIGIN"
    assert "frame-ancestors 'self'" in page.headers["content-security-policy"]
    assert page.headers["x-content-type-options"] == "nosniff"


def test_too_many_wrong_passwords_lock_that_address(server, monkeypatch):
    monkeypatch.setattr(server, "settings", replace(server.settings, password="open sesame"))
    monkeypatch.setattr(server.asyncio, "sleep", _no_wait)
    client = TestClient(server.app)
    phone = {"x-forwarded-for": "100.64.0.9"}
    for _ in range(server.LOGIN_TRIES):
        assert client.post("/login", data={"password": "guess"}, headers=phone).status_code == 401
    locked = client.post("/login", data={"password": "open sesame"}, headers=phone, follow_redirects=False)
    assert locked.status_code == 429 and "Too many" in locked.text
    # Another address (the PC itself) is not locked out.
    ok = client.post("/login", data={"password": "open sesame"}, follow_redirects=False)
    assert ok.status_code == 303 and "jarvis_session" in ok.headers["set-cookie"]


async def _no_wait(_seconds):
    return None


def test_a_failed_turn_still_lets_the_page_listen_again(server, monkeypatch):
    async def broken(self, text, speak):
        raise RuntimeError("boom")

    monkeypatch.setattr(server.Brain, "handle", broken)
    with TestClient(server.app) as client:
        with client.websocket_connect("/ws", headers={"origin": "http://testserver"}) as ws:
            ws.receive_json()  # alerts
            ws.send_json({"text": "hello"})
            assert ws.receive_json()["type"] == "note"
            assert ws.receive_json() == {"type": "done"}
            ws.send_json({"text": "again"})  # the worker is still alive
            assert ws.receive_json()["type"] == "note"
            assert ws.receive_json() == {"type": "done"}


def test_the_voice_starts_after_the_first_sentence():
    assert tts.speaking_parts("Right. Good morning sir, it is sunny! More here? And more.") == [
        "Right. Good morning sir, it is sunny!", "More here? And more."]
    assert tts.speaking_parts("Hello there.") == ["Hello there."]
    assert tts.speaking_parts("  ") == []


async def test_elevenlabs_failing_hands_the_rest_to_the_browser_voice():
    calls = []

    def answer(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, content=b"MP3")
        raise httpx.ConnectTimeout("slow")

    settings = Settings(elevenlabs_api_key="key")
    async with httpx.AsyncClient(transport=httpx.MockTransport(answer)) as http:
        parts = [p async for p in tts.stream(http, settings, "Good morning sir, it is sunny. Rain later. Bring a coat.")]
        assert parts == [("Good morning sir, it is sunny.", b"MP3"), ("Rain later. Bring a coat.", None)]
        assert await tts.synthesize(http, settings, "Hi.") is None  # a network error is not a crash

    async with httpx.AsyncClient() as http:
        assert [p async for p in tts.stream(http, Settings(elevenlabs_api_key=""), "Hi.")] == [("Hi.", None)]


def test_the_page_can_check_the_line_is_alive_mid_turn(server, monkeypatch):
    import asyncio

    async def slow(self, text, speak):
        await asyncio.sleep(30)

    monkeypatch.setattr(server.Brain, "handle", slow)
    with TestClient(server.app) as client:
        with client.websocket_connect("/ws", headers={"origin": "http://testserver"}) as ws:
            ws.receive_json()  # alerts
            ws.send_json({"text": "research everything"})
            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}  # answered even while he's busy
            ws.send_json({"type": "cancel"})
            assert ws.receive_json() == {"type": "note", "text": "Cancelled."}
            assert ws.receive_json() == {"type": "done"}


def test_the_page_fingerprint_changes_only_when_its_files_change(server, tmp_path, monkeypatch):
    (tmp_path / "main.js").write_text("one")
    (tmp_path / "custom.css").write_text("mine")
    monkeypatch.setattr(server, "FRONTEND", tmp_path)
    first = server.frontend_build()
    assert server.frontend_build() == first
    (tmp_path / "custom.css").write_text("my new colours")  # personal styling doesn't force a reload
    assert server.frontend_build() == first
    (tmp_path / "main.js").write_text("two")
    assert server.frontend_build() != first
