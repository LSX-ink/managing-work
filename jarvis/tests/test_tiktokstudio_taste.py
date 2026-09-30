"""TikTok studio: tick / X approval, learning the user's taste, clipping only streamers who allow it, n3on.vault's
100k+ extended Kick clips and the HUD's queue endpoint. No network, yt-dlp or Claude: all mocked."""

import asyncio
import json
from dataclasses import replace
from datetime import date

import httpx
import pytest

import kick
import tiktokstudio as creator
import tiktokstudio_clips as clips
import tiktokstudio_store as cs
import tiktokstudio_video as cv
import twitch
from config import Settings
from tests.test_tiktokstudio import SCRIPT, FakeClient, add_video, allow, clip


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), tiktok_client_key="", tiktok_client_secret="")


@pytest.fixture(autouse=True)
def idle_studio():
    creator._ctx.update(client=None, http=None, announce=None, making=False, views_at=0.0, pending=[])
    yield


def run_and_wait(coro):
    """Run a studio call, then let the replacement it started in the background finish."""
    async def go():
        out = await coro
        while creator._tasks:
            await asyncio.gather(*list(creator._tasks))
        return out
    return asyncio.run(go())


def fake_story(seen):
    async def fake_make(client, http, settings, account, folder, idea="", recent=None, script=None, best=None, taste=""):
        seen.append({"idea": idea, "taste": taste, "account": account["name"]})
        path = folder / f"New {len(seen)}.mp4"
        path.write_bytes(b"mp4")
        return {**cv.parse_script(SCRIPT), "title": "The Better One", "path": path}
    return fake_make


# ---- tick and X ----------------------------------------------------------------------------------------------

def test_reject_marks_it_and_makes_a_better_one_straight_away(s, monkeypatch):
    seen, said_aloud = [], []

    async def say(text, kind):
        said_aloud.append(text)
    monkeypatch.setattr(cv, "make", fake_story(seen))
    creator._ctx.update(client=object(), announce=say)
    first = add_video(s, hook="She never deleted it.")
    said = run_and_wait(creator.run_tool("tiktok_studio", {"action": "reject", "video": "lowkey.lore",
                                                           "reason": "too slow"}, s))
    assert "Rejected 'The Last Voicemail'" in said and "better one for lowkey.lore" in said
    data = cs.load(s)
    old = next(v for v in data["videos"] if v["id"] == first["id"])
    assert old["status"] == "rejected" and old["reason"] == "too slow"
    new = data["videos"][-1]
    assert new["status"] == "ready" and new["replaces"] == first["id"] and new["account"] == "lowkey.lore"
    assert "REPLACES 'The Last Voicemail'" in seen[0]["idea"] and "too slow" in seen[0]["idea"]
    assert "REJECTED" in seen[0]["taste"] and "too slow" in seen[0]["taste"]
    assert "ready for you to approve" in said_aloud[-1]
    # a rejected video can't be rejected or approved again, and it doesn't count towards the day's videos
    with pytest.raises(ValueError):
        asyncio.run(creator.reject(s, first["id"]))
    with pytest.raises(ValueError):
        asyncio.run(creator.approve(s, first["id"]))
    assert cs.made_today(cs.load(s), "lowkey.lore") == 1


def test_reject_that_one_takes_the_newest_waiting_video(s):
    add_video(s, title="Waiting One")
    add_video(s, title="Posted One", status="posted")
    said = asyncio.run(creator.run_tool("tiktok_studio", {"action": "reject", "video": "that one"}, s))
    assert "Waiting One" in said and "restart" in said  # the studio isn't running in this test
    assert "rejected" in cs.find_video(cs.load(s), "Waiting One")["status"]


def test_a_reject_while_busy_waits_its_turn(s, monkeypatch):
    seen = []
    monkeypatch.setattr(cv, "make", fake_story(seen))
    creator._ctx.update(client=object())

    async def go():
        creator._ctx["making"] = True  # another video is being made
        await creator.make_in_background(s, [("lowkey.lore", "", None, {"id": "x", "title": "Old"})])
        assert seen == [] and len(creator._ctx["pending"]) == 1
        creator._ctx["making"] = False
        await creator.make_in_background(s, [])
    asyncio.run(go())
    assert "REPLACES 'Old'" in seen[0]["idea"]


# ---- taste -------------------------------------------------------------------------------------------------

def test_ticks_and_xs_are_learned_and_go_into_the_script_prompt(s):
    add_video(s, title="Midnight Tapes 1", hook="The tape had my voice on it.", notes="noir look")
    asyncio.run(creator.approve(s, "midnight"))
    add_video(s, title="Boring Kitchen", hook="She made toast.")
    asyncio.run(creator.reject(s, "boring", "nothing happens"))
    account = cs.account(cs.load(s), "lowkey.lore")
    summary = cs.taste_summary(account)
    assert "APPROVED: 'Midnight Tapes 1', hook: The tape had my voice on it., noir look" in summary
    assert "REJECTED: 'Boring Kitchen', hook: She made toast. (why: nothing happens)" in summary
    client = FakeClient([(SCRIPT, "end_turn")])
    asyncio.run(cv.write_script(client, s, account, idea=creator.replace_idea(cs.find_video(cs.load(s), "boring"))))
    prompt = client.calls[0]["messages"][0]["content"]
    assert "Midnight Tapes 1" in prompt and "nothing happens" in prompt and "never a copy" in prompt
    assert "REPLACES 'Boring Kitchen'" in prompt and "clearly better" in prompt
    # a renamed account keeps what it learned
    creator.update_account(s, {"account": "lowkey.lore", "new_name": "lowkey.tapes"})
    assert cs.account(cs.load(s), "lowkey.tapes")["taste"]["liked"][0]["title"] == "Midnight Tapes 1"


def test_no_taste_yet_asks_for_something_fresh(s):
    assert "fresh" in cs.taste_summary(cs.account(cs.load(s), "lowkey.lore"))


def test_clip_picks_are_told_the_taste_and_what_they_replace(s):
    account = cs.account(cs.load(s), "n3on.vault")
    cs.remember(account, {"title": "N3on rage quits", "notes": "old clips"}, True)
    client = FakeClient([('{"order": ["c2", "zz"], "hook": "He did NOT see this coming"}', "end_turn")])
    ordered, hook = asyncio.run(clips.choose(client, s, account, [clip(1), clip(2)],
                                             {"title": "Dull one", "reason": "too long"}))
    assert [c["id"] for c in ordered] == ["c2", "c1"] and hook == "He did NOT see this coming"
    prompt = client.calls[0]["messages"][0]["content"]
    assert "N3on rage quits" in prompt and "REPLACES 'Dull one'" in prompt and "too long" in prompt
    # without Claude the most-viewed order stays
    assert asyncio.run(clips.choose(None, s, account, [clip(1), clip(2)]))[0][0]["id"] == "c1"


# ---- only streamers who allow clipping -------------------------------------------------------------------------

def test_only_streamers_who_allow_clipping_are_clipped(s):
    account = cs.new_account("x", format="clips", streamers=[
        {"name": "kai", "platform": "twitch", "allows_clipping": True},
        {"name": "ish", "platform": "twitch", "allows_clipping": False}, "bare",
        {"name": "n3on", "platform": "kick", "allows_clipping": True}])
    assert cs.allowed(account) == ["kai", "n3on"] and cs.allowed(account, "kick") == ["n3on"]
    found = [clip(1, "kai"), clip(2, "ish"), clip(3, "bare"), {**clip(4, "N3on"), "platform": "kick", "channel": "n3on"},
             {**clip(5, "kai"), "platform": "kick", "channel": "kai"}]  # kai allowed on Twitch, not on Kick
    assert [c["id"] for c in clips.guard(found, account)] == ["c1", "c4"]
    nobody = cs.new_account("y", format="clips", streamers=["kai"])
    with pytest.raises(ValueError, match="allow clipping"):
        asyncio.run(clips.make(None, s, nobody, s.memory_dir, "new"))
    assert "allow clipping" in creator.clips_blocked(s, nobody)


def test_clips_from_streamers_not_allowed_never_reach_a_video(s, monkeypatch):
    s = replace(s, twitch_client_id="id", twitch_client_secret="sec")
    allow(s, "Clipzz", "kai")

    async def fake_top(http, settings, era, streamers, category):
        assert streamers == ["kai"]
        return [clip(1, "stranger", 60, 99999), clip(2, "stranger", 30, 9999), clip(3, "kai", 40, 10), clip(4, "kai", 30, 5)]
    monkeypatch.setattr(twitch, "top_clips", fake_top)
    got = []
    monkeypatch.setattr(clips, "download", lambda url, target, section=None: (got.append(url), target.with_suffix(".mp4").write_bytes(b"c"), target.with_suffix(".mp4"))[2])
    monkeypatch.setattr(clips, "portrait", lambda source, layer, out: out.write_bytes(b"p"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    asyncio.run(creator.make_in_background(s, [("Clipzz", "", None)]))
    assert cs.load(s)["videos"][-1]["status"] == "ready" and got == ["https://clips.twitch.tv/c3", "https://clips.twitch.tv/c4"]


# ---- n3on.vault: 100k+ Kick clips, extended from the stream ----------------------------------------------------

def kick_clip(i, views, seconds=40, started="2026-09-20T12:10:00.000Z", created="2026-09-20T12:10:45.000Z"):
    return {"id": f"clip_{i}", "title": f"N3on moment {i}", "views": views, "duration": seconds, "livestream_id": 77,
            "started_at": started, "created_at": created, "channel": {"slug": "n3on", "username": "N3on"}}


VOD = {"id": 77, "start_time": "2026-09-20 12:00:00", "duration": 3 * 3600 * 1000, "video": {"uuid": "5c697a87-afce-4256-b01f-3c8fe71ef5cb"}}


def neon_fakes(monkeypatch, pages, vods):
    asked, cuts = [], []

    def fake_json(url):
        asked.append(url)
        if url.endswith("/videos"):
            return vods
        return pages.pop(0)
    monkeypatch.setattr(kick, "get_json", fake_json)

    def fake_download(url, target, section=None):
        cuts.append((url, section))
        out = target.with_suffix(".mp4")
        out.write_bytes(b"c")
        return out
    monkeypatch.setattr(clips, "download", fake_download)
    monkeypatch.setattr(clips, "portrait", lambda source, layer, out: out.write_bytes(b"p"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    return asked, cuts


def test_neon_takes_only_100k_clips_and_extends_them_from_the_stream(s, monkeypatch):
    account = cs.account(cs.load(s), "n3on.vault")
    assert account["min_views"] == 100_000 and account["extend"] == 30 and cs.allowed(account, "kick") == ["n3on"]
    pages = [{"clips": [kick_clip(1, 99_999), kick_clip(2, 250_000)], "nextCursor": "abc"},
             {"clips": [kick_clip(3, 120_000)], "nextCursor": None}]
    asked, cuts = neon_fakes(monkeypatch, pages, [VOD])
    asyncio.run(creator.make_in_background(s, [("n3on.vault", "", None)]))
    v = cs.load(s)["videos"][-1]
    assert v["status"] == "ready", v.get("error")
    assert "sort=view" in asked[0] and "cursor=abc" in asked[1] and asked[0].startswith("https://kick.com/api/v2/channels/n3on/clips")
    # the most-viewed 100k+ clip, cut again from its VOD with 30s either side (it starts 600s into the stream)
    assert cuts == [("https://kick.com/n3on/videos/5c697a87-afce-4256-b01f-3c8fe71ef5cb", (570.0, 670.0))]
    assert v["clip_ids"] == ["clip_2"] and "Extended cut" in v["caption"] and "N3on" in v["caption"] and "kick" in v["hashtags"]
    assert cs.account(cs.load(s), "n3on.vault")["used_clips"] == ["clip_2"]
    assert v["keyword"] == "new" and "time=week" in asked[0] and "extended cut" in v["notes"]


def test_neon_falls_back_to_the_plain_clip_and_never_reuses_one(s, monkeypatch):
    data = cs.load(s)
    cs.account(data, "n3on.vault")["used_clips"] = ["clip_2"]
    cs.save(s, data)
    pages = [{"clips": [kick_clip(2, 900_000), kick_clip(3, 400_000, 35), kick_clip(4, 300_000, 30)]}]
    _, cuts = neon_fakes(monkeypatch, pages, [])  # the streams are gone: no offsets
    asyncio.run(creator.make_in_background(s, [("n3on.vault", "", None)]))
    v = cs.load(s)["videos"][-1]
    assert v["status"] == "ready" and v["clip_ids"] == ["clip_3", "clip_4"]
    assert cuts == [("https://kick.com/n3on/clips/clip_3", None), ("https://kick.com/n3on/clips/clip_4", None)]
    assert "Extended" not in v["caption"]


def test_neon_says_clearly_when_kick_cant_be_reached(s, monkeypatch):
    def offline(url):
        raise OSError("Network is unreachable")
    monkeypatch.setattr(kick, "get_json", offline)
    asyncio.run(creator.make_in_background(s, [("n3on.vault", "", None)]))
    v = cs.load(s)["videos"][-1]
    assert v["status"] == "failed" and "couldn't reach the clips for n3on.vault" in v["error"]
    assert "Network is unreachable" in v["error"]


def test_extension_offsets():
    assert clips.extension(100, 40) == (70, 170)
    assert clips.extension(10, 40) == (0, 80)  # can't start before the stream
    assert clips.extension(3590, 20, length=3600) == (3560, 3600)  # nor end after it
    row = kick.clip_row(kick_clip(1, 5), "n3on")
    assert kick.vod_offset(row, [VOD]) == ("https://kick.com/n3on/videos/5c697a87-afce-4256-b01f-3c8fe71ef5cb", 600.0, 10800.0)
    assert kick.vod_offset(row, [{**VOD, "id": 5}]) is None  # a different stream
    stale = kick.clip_row(kick_clip(1, 5, started="2026-09-20T09:00:00Z"), "n3on")  # not the clip's own start
    assert kick.vod_offset(stale, [VOD]) is None


def test_twitch_clips_carry_their_vod_offset(s, monkeypatch):
    s = replace(s, twitch_client_id="id", twitch_client_secret="sec")

    async def fake_top(http, settings, era, streamers, category):
        return [{**clip(1, "n3on", 30, 200_000), "video_id": "123", "vod_offset": 900}, clip(2, "n3on", 30, 150_000)]
    monkeypatch.setattr(twitch, "top_clips", fake_top)
    monkeypatch.setattr(kick, "get_json", lambda url: [] if url.endswith("/videos") else {"clips": []})
    account = cs.account(cs.load(s), "n3on.vault")
    found = asyncio.run(clips.sources(None, s, account, "new"))
    assert found[0]["vod"] == ("https://www.twitch.tv/videos/123", 900.0, 0.0) and "vod" not in found[1]


def test_kick_keys_are_optional_and_checked_when_set(s):
    assert not kick.configured(s)
    asyncio.run(kick.check_channel(None, s, "n3on"))  # no keys: nothing to check
    s = replace(s, kick_client_id="kid", kick_client_secret="ksec")
    kick._token.update(value="", until=0)

    def handler(request):
        if request.url.host == "id.kick.com":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        assert request.headers["authorization"] == "Bearer t" and request.url.params["slug"] == "n3onn"
        return httpx.Response(200, json={"data": []})
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="no channel called n3onn"):
        asyncio.run(kick.check_channel(http, s, "n3onn"))


def test_neon_is_made_daily_without_any_keys(s):
    jobs = creator.todays_jobs(s, cs.load(s), date.today())
    assert [j[0] for j in jobs].count("n3on.vault") == 3


# ---- the HUD's queue -----------------------------------------------------------------------------------------

def test_queue_endpoint_and_json_tick_and_x(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    from fastapi.testclient import TestClient
    import server

    s = Settings(memory_dir=str(tmp_path / "m"), password="", creator_daily=False)
    monkeypatch.setattr(server, "settings", s)
    story = add_video(s, title="Story One", made_at="2026-09-30 07:10")
    (tmp_path / "m" / story["file"]).with_suffix(".png").write_bytes(b"png")
    clip_video = add_video(s, account="n3on.vault", title="N3on moment")
    add_video(s, title="Old One", status="posted")
    started = []

    async def no_remake(settings, jobs):
        started.extend(jobs)
    monkeypatch.setattr(creator, "make_in_background", no_remake)
    page = {"origin": "http://testserver"}
    with TestClient(server.app) as client:
        rows = client.get("/creator/queue").json()
        assert [r["id"] for r in rows] == [story["id"], clip_video["id"]]
        assert rows[0]["kind"] == "story" and rows[1]["kind"] == "clip" and rows[0]["created"] == "2026-09-30 07:10"
        assert rows[0]["thumb_url"].endswith(".png") and rows[1]["thumb_url"] is None
        assert client.get(rows[0]["video_url"]).content == b"\x00" * 1000
        assert client.post(f"/creator/videos/{story['id']}/reject").status_code == 403
        x = client.post(f"/creator/videos/{clip_video['id']}/reject", headers=page, json={"reason": "cut too early"})
        assert x.json()["ok"] is True and "Rejected 'N3on moment'" in x.json()["said"]
        assert started[0][0] == "n3on.vault" and started[0][3]["reason"] == "cut too early"
        tick = client.post(f"/creator/videos/{story['id']}/approve", headers=page).json()
        assert tick["ok"] is True and "Approved" in tick["said"] and tick["card"]["kind"] == "creator-studio"
        again = client.post(f"/creator/videos/{story['id']}/reject", headers=page)
        assert again.status_code == 400 and again.json()["ok"] is False
        assert client.get("/creator/queue").json() == []
    data = cs.load(s)
    assert cs.find_video(data, clip_video["id"])["reason"] == "cut too early"
    taste = cs.account(data, "n3on.vault")["taste"]
    assert taste["rejected"][0]["reason"] == "cut too early"
    assert cs.account(data, "lowkey.lore")["taste"]["liked"][0]["title"] == "Story One"


def test_the_tool_offers_reject_with_a_reason():
    tool = creator.tool_definitions()[0]
    assert "reject" in tool["input_schema"]["properties"]["action"]["enum"]
    assert "reason" in tool["input_schema"]["properties"]
    assert "I don't like the lowkey.lore video" in tool["description"] and "reject that one" in tool["description"]
    json.dumps(tool)



def test_pause_stops_making_content(s):
    creator._ctx["pending"].append(("lowkey.lore", "", None))
    said = asyncio.run(creator.run_tool("tiktok_studio", {"action": "pause"}, s))
    assert "paused" in said and not creator._ctx["pending"] and cs.load(s)["paused"] is True
    add_video(s)
    said = run_and_wait(creator.reject(s, "latest"))
    assert "won't make a replacement" in said and not creator._ctx["pending"]
    said = asyncio.run(creator.run_tool("tiktok_studio", {"action": "resume"}, s))
    assert "back on" in said and cs.load(s)["paused"] is False
