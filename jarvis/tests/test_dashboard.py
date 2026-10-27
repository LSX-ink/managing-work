from dataclasses import replace
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from hq import dashboard

LIST = """# Instagram DMs for Tuesday 27 October

Intro.

## 1. Kamo Barbers Newcastle (Newcastle)
Instagram: @kamo.barbersnewcastle
4.8★ from 1037 Google reviews
Mock-up: https://kineticwebdesigns.co.uk/m/kamo/


```
Hi Kamo Barbers team

Kinetic Web Designs
```

## 2. Gents & Rascals BarberShop - HSBC Tower (Auckland)
Instagram: @gents_and_rascals
Mock-up (cinema design): https://kineticwebdesigns.co.uk/m/gents-v2/
Checks: all passed

```
Hi Gents team
```
"""


def test_todays_dms_are_read_from_the_list():
    dms = dashboard.parse_dms(LIST)
    assert [d["name"] for d in dms] == ["Kamo Barbers Newcastle", "Gents & Rascals BarberShop - HSBC Tower"]
    assert dms[0]["instagram"] == "kamo.barbersnewcastle" and dms[0]["link"] == "https://kineticwebdesigns.co.uk/m/kamo/"
    assert dms[0]["dm"] == "Hi Kamo Barbers team\n\nKinetic Web Designs" and dms[1]["town"] == "Auckland"
    assert dms[1]["link"] == "https://kineticwebdesigns.co.uk/m/gents-v2/"


def test_the_rebuilt_list_wins_over_the_morning_one(tmp_path):
    day = date(2026, 10, 27)
    assert dashboard.dm_file(day, tmp_path) is None
    (tmp_path / "Instagram DMs 2026-10-27.md").write_text("a")
    assert dashboard.dm_file(day, tmp_path).name == "Instagram DMs 2026-10-27.md"
    (tmp_path / "Instagram DMs 2026-10-27 (new designs).md").write_text("b")
    assert dashboard.dm_file(day, tmp_path).name == "Instagram DMs 2026-10-27 (new designs).md"


def test_claudes_work_now_done_and_waiting(tmp_path):
    dashboard.work_update(tmp_path, "now", "Rebuilding sites", "", "half an hour")
    w = dashboard.work_update(tmp_path, "wait", "Merge on GitHub", "https://github.test/compare")
    assert w["now"]["title"] == "Rebuilding sites" and w["waiting"][0]["link"] == "https://github.test/compare"
    w = dashboard.work_update(tmp_path, "done", "Rebuilding sites", "https://k.test/")
    assert w["now"] == {} and w["done"][0]["title"] == "Rebuilding sites"
    w = dashboard.work_update(tmp_path, "clear-wait", "Merge on GitHub")
    assert w["waiting"] == [] and dashboard.load_work(tmp_path)["done"][0]["link"] == "https://k.test/"
    with pytest.raises(ValueError):
        dashboard.work_update(tmp_path, "explode")


def test_the_sent_button_marks_the_lead_messaged_by_dm(tmp_path):
    from config import Settings
    s = Settings(memory_dir=str(tmp_path))
    assert "Kamo" in dashboard.mark_sent(s, "Kamo Barbers")
    assert "kamo barbers" in dashboard.messaged_today(s, date.today())


def test_only_the_dashboard_goes_through_alfred_behind_his_login(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    import server
    seen = []

    def hq(request):
        seen.append((request.method, request.url.path))
        return httpx.Response(200, json={"ok": True})
    monkeypatch.setattr(server, "settings", replace(server.settings, password="open sesame"))
    with TestClient(server.app) as client:
        server.app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(hq))
        assert client.get("/hq/api/dashboard").status_code == 401  # not logged in
        client.post("/login", data={"password": "open sesame"})
        assert client.get("/hq/api/dashboard").json() == {"ok": True}
        assert client.post("/hq/api/dm/sent", json={"name": "Kamo"}).status_code == 200
        assert client.post("/hq/api/run/closer").status_code == 404  # the HQ controls stay on the PC
        assert client.get("/hq/api/settings").status_code == 404
    assert seen == [("GET", "/api/dashboard"), ("POST", "/api/dm/sent")]
