import asyncio
import inspect
import time

import pytest

import station
import tiktokstudio_store as cs
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def store(s, videos):
    data = cs.load(s)
    data["accounts"].append(cs.new_account("n3on.vault", style="clips", format="clips"))
    data["videos"] = videos
    cs.save(s, data)


def ago(hours):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - hours * 3600))


def test_idle_when_nothing_is_happening(s):
    out = station.state(s)
    assert out["phase"] == "idle" and out["making"] == 0 and out["ready"] == 0
    assert out["waiting"] == [] and out["approvals"] == []
    assert [a["name"] for a in out["accounts"]][:4] == ["lowkey.lore", "mindglitch.fyi", "karma.receipts", "Clipzz"]


def test_state_maps_the_studio_store(s):
    store(s, [
        {"id": "v1", "account": "lowkey.lore", "status": "making", "title": "Being made", "made_at": ago(0)},
        {"id": "v2", "account": "lowkey.lore", "status": "ready", "title": "Last Voicemail", "made_at": ago(1),
         "file": "Work/TikTok/lowkey.lore/Last Voicemail.mp4"},
        {"id": "v3", "account": "n3on.vault", "status": "ready", "title": "Wild clutch", "made_at": ago(2)},
        {"id": "v4", "account": "karma.receipts", "status": "posted", "title": "Karma", "posted_at": ago(3)},
        {"id": "v5", "account": "karma.receipts", "status": "approved", "title": "Old one", "posted_at": ago(48)},
        {"id": "v6", "account": "mindglitch.fyi", "status": "skipped", "title": "Nope"},
        {"id": "v7", "account": "mindglitch.fyi", "status": "failed", "title": "Broke"},
    ])
    out = station.state(s)
    assert out["phase"] == "waiting" and out["making"] == 1 and out["ready"] == 2
    by = {a["name"]: a for a in out["accounts"]}
    assert by["lowkey.lore"]["making"] == 1 and by["lowkey.lore"]["ready"] == 1
    assert by["n3on.vault"]["ready"] == 1 and by["n3on.vault"]["colour"] == "#39ffb0"
    assert by["n3on.vault"]["label"] == "TWITCH CLIPS · CLIPS"
    assert by["karma.receipts"]["approved"] == 1 and by["karma.receipts"]["last_approved"] == ago(3)
    assert by["mindglitch.fyi"]["making"] == by["mindglitch.fyi"]["ready"] == 0
    first = out["waiting"][0]
    assert set(first) == {"id", "account", "title", "kind", "created", "video_url", "thumb_url"}
    assert first["id"] == "v2" and first["kind"] == "story" and first["created"] == ago(1)
    assert first["video_url"].startswith("/screen/file?path=Work/TikTok/lowkey.lore/Last%20Voicemail.mp4")
    assert out["waiting"][1]["video_url"] == "" and out["waiting"][1]["kind"] == "clips"
    assert [a["id"] for a in out["approvals"]] == ["v4"]  # the two-day-old approval isn't recent


def test_making_without_waiting(s):
    store(s, [{"id": "v1", "account": "Clipzz", "status": "making", "title": "Being made"}])
    out = station.state(s)
    assert out["phase"] == "making" and out["waiting"] == []


def test_paused_content_keeps_the_ship_grounded(s):
    store(s, [{"id": "v1", "account": "lowkey.lore", "status": "ready", "title": "Waiting"}])
    data = cs.load(s); data["paused"] = True; cs.save(s, data)
    out = station.state(s)
    assert out["phase"] == "idle" and out["paused"] is True
    assert out["ready"] == 1 and out["waiting"][0]["id"] == "v1"  # still there to tick or cross


def test_ground_and_fly_actions(s):
    assert station.run_tool("station_view", {"action": "ground"}, s).card["data"]["action"] == "ground"
    assert station.run_tool("station_view", {"action": "launch"}, s).card["data"]["action"] == "fly"


def test_station_view_signature_and_results(s):
    assert station in tools.ABILITIES
    inspect.signature(station.run_tool).bind("name", {}, None, None)  # name, args, settings, http
    names = {t["name"] for t in station.tool_definitions()}
    assert names == station.NAMES == {"station_view"}
    for action in station.ACTIONS:
        shown = station.run_tool("station_view", {"action": action}, s, None)
        assert shown == station.ACTIONS[action]
        assert shown.card["kind"] == "station" and shown.card["data"] == {"action": action}
    assert station.run_tool("station_view", {"action": "go to LSX".split()[-1]}, s).card["data"]["action"] == "lsx"
    assert station.run_tool("station_view", {"action": "deep space"}, s).card["data"]["action"] == "deep"
    with pytest.raises(ValueError):
        station.run_tool("station_view", {"action": "warp"}, s)


def test_station_view_through_alfred_pushes_a_card(s):
    sent = []

    async def page(msg):
        sent.append(msg)

    async def go():
        return await tools.run_tool("station_view", {"action": "night"}, s, None, page)

    assert asyncio.run(go()) == "Night mode at the bases."
    assert sent == [{"type": "popup", "card": {"kind": "station", "title": "Station", "id": "station-view",
                                                "buttons": [], "data": {"action": "night"}}}]


def test_video_making_and_the_ship_are_never_hidden_behind_tool_search():
    from dataclasses import replace

    import brain
    import tiktokstudio
    import tools
    from config import Settings

    assert {tiktokstudio, station} <= tools.ALWAYS_LOADED
    loaded = {t["name"] for t in brain.request_options(replace(Settings(), model="claude-opus-5"))["tools"]
              if "name" in t and not t.get("defer_loading")}
    assert {"tiktok_studio", "station_view"} <= loaded
