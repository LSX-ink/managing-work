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
