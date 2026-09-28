import json
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def test_page_can_be_added_to_a_phone_home_screen():
    page = (FRONTEND / "index.html").read_text()
    assert '<link rel="manifest" href="/static/app/manifest.webmanifest">' in page
    assert '<link rel="apple-touch-icon" href="/static/app/icon-180.png">' in page
    manifest = json.loads((FRONTEND / "app" / "manifest.webmanifest").read_text())
    assert manifest["name"] == "Alfred" and manifest["display"] == "standalone"
    for icon in manifest["icons"]:
        assert (FRONTEND / icon["src"].removeprefix("/static/")).read_bytes().startswith(b"\x89PNG")


def test_phone_link_needs_a_password(monkeypatch):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    import server

    phone = {"x-forwarded-for": "100.101.102.103", "tailscale-user-login": "me@example.com"}
    monkeypatch.setattr(server, "settings", replace(server.settings, password=""))
    client = TestClient(server.app)
    assert client.get("/").status_code == 200  # on the PC itself nothing changes
    locked = client.get("/", headers=phone)
    assert locked.status_code == 403 and "JARVIS_PASSWORD" in locked.text
    assert client.get("/config", headers=phone).status_code == 403

    monkeypatch.setattr(server, "settings", replace(server.settings, password="open sesame"))
    assert "Unlock" in client.get("/", headers=phone).text  # with a password the phone gets the login page
    assert client.get("/config", headers=phone).status_code == 401
