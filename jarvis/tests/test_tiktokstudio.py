import asyncio
import json
import time
from dataclasses import replace
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from PIL import Image

import tiktokstudio as creator
import tiktokstudio_store as cs
import tiktokstudio_video as cv
import money_research
import screen
import tiktok
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), tiktok_client_key="", tiktok_client_secret="")


@pytest.fixture(autouse=True)
def idle_studio():
    creator._ctx.update(client=None, http=None, announce=None, making=False, views_at=0.0, pending=[])
    yield


def studio(s, **a):
    return asyncio.run(creator.run_tool("tiktok_studio", a, s))


SCRIPT = json.dumps({"title": "The Last Voicemail", "keyword": "Unsent #1", "hook": "She never deleted it.",
                     "caption": "Would you listen?", "hashtags": ["#Story", "ai story"],
                     "scenes": [{"text": "She pressed play.", "narration": "She pressed play again.", "picture": "a phone"},
                                {"text": "It said her name.", "narration": "And it said her name.", "picture": "a kitchen"}]})


def add_video(s, **fields):
    data = cs.load(s)
    folder = cs.work_folder(s, "TikTok", fields.get("account", "lowkey.lore"))
    (folder / "clip.mp4").write_bytes(b"\x00" * 1000)
    v = {"id": cs.new_id() + str(len(data["videos"])), "account": "lowkey.lore", "day": date.today().isoformat(),
         "status": "ready", "title": "The Last Voicemail", "caption": "Would you listen?", "hashtags": ["story"],
         "file": cs.relative(s, folder / "clip.mp4"), "part": 1, "views": 0, **fields}
    data["videos"].append(v)
    cs.save(s, data)
    return v


# ---- accounts ------------------------------------------------------------------------------------------

def test_starts_with_flashy_accounts_in_the_looks_the_user_liked(s):
    data = cs.load(s)
    assert [a["name"] for a in data["accounts"]] == ["lowkey.lore", "mindglitch.fyi", "karma.receipts", "Clipzz", "n3on.vault"]
    assert [a["style"] for a in data["accounts"]] == ["noir", "explainer", "drama", "clips", "clips"]
    assert [a["per_day"] for a in data["accounts"]] == [3, 3, 3, 5, 3]


def test_clipzz_joins_a_studio_made_before_it(s):
    old = {"accounts": [cs.new_account(**cs.STARTERS[0])], "videos": []}
    (Path(s.memory_dir) / cs.FILE).write_text(json.dumps(old), encoding="utf-8")
    assert [a["name"] for a in cs.load(s)["accounts"]] == ["lowkey.lore", "Clipzz", "n3on.vault"]
    data = cs.load(s)
    data["accounts"].pop()  # removed on purpose: it stays removed
    cs.save(s, data)
    assert [a["name"] for a in cs.load(s)["accounts"]] == ["lowkey.lore", "Clipzz"]


def test_add_rename_and_remove_accounts(s):
    assert "Added ghost.gossip" in studio(s, action="add_account", account="@ghost.gossip", theme="ghost stories",
                                          style="cinematic", per_day=2)
    assert "already" in pytest.raises(ValueError, studio, s, action="add_account", account="ghost.gossip").value.args[0]
    add_video(s, account="ghost.gossip")
    studio(s, action="update_account", account="ghost", new_name="spooky.szn", per_day=9)
    data = cs.load(s)
    renamed = cs.account(data, "spooky.szn")
    assert renamed["theme"] == "ghost stories" and renamed["per_day"] == 6 and renamed["style"] == "cinematic"
    assert data["videos"][-1]["account"] == "spooky.szn"
    assert "confirm" in studio(s, action="remove_account", account="spooky.szn")
    studio(s, action="remove_account", account="spooky.szn", confirmed=True)
    assert cs.find_account(cs.load(s), "spooky.szn") is None
    shown = studio(s, action="accounts")
    assert shown.card["rows"][0][:2] == ["lowkey.lore", "noir"] and shown.card["rows"][0][4] == "no"


def test_name_ideas_asks_for_gen_z_names(s):
    said = studio(s, action="name_ideas", theme="horror stories")
    assert "Gen Z" in said and "horror stories" in said


# ---- making videos ---------------------------------------------------------------------------------------

def test_parse_script_tidies_claudes_reply():
    script = cv.parse_script("Here you go:\n```json\n" + SCRIPT + "\n```")
    assert script["title"] == "The Last Voicemail" and len(script["scenes"]) == 2
    assert script["hashtags"] == ["story", "aistory"]
    with pytest.raises(ValueError):
        cv.parse_script('{"title": "x", "scenes": [{"text": "one"}]}')


def test_videos_last_at_least_a_minute():
    assert sum(cv.fit_to_length([4.0] * 8)) == pytest.approx(61.0)
    assert sum(cv.fit_to_length([9.0] * 10)) == pytest.approx(93.5, abs=0.2)  # a longer story keeps its length
    assert min(cv.fit_to_length([2, 20])) > 2.35


def test_every_look_makes_a_full_size_frame():
    pic = Image.new("RGB", (800, 600), (120, 90, 60))
    script = cv.parse_script(SCRIPT)
    for style in cs.STYLES:
        im = cv.frame(pic, {"name": "x", "style": style, "accent": "#ff0000"}, script, script["scenes"][0])
        assert im.size == (cv.W, cv.H)


def test_a_missing_picture_or_voice_still_makes_a_video(s, tmp_path, monkeypatch):
    rendered = []
    monkeypatch.setattr(cv, "render_scene", lambda still, voice, seconds, out, *a: (rendered.append((voice, seconds)), out.write_bytes(b"v")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    account = cs.load(s)["accounts"][0]
    out = asyncio.run(cv.make(None, None, s, account, tmp_path, script=cv.parse_script(SCRIPT)))
    assert out["path"].read_bytes() == b"mp4" and out["missing_pictures"] == 2
    assert out["path"].with_suffix(".png").exists()
    assert "#story" in out["path"].with_suffix(".md").read_text(encoding="utf-8")
    assert sum(sec for _, sec in rendered) == pytest.approx(61.0) and all(v is None for v, _ in rendered)
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".")] == []


def test_studio_makes_a_video_and_queues_it(s, monkeypatch):
    announced = []

    async def fake_make(client, http, settings, account, folder, idea="", recent=None, script=None, best=None, taste="", part=1, variety=""):
        path = folder / "Clip.mp4"
        path.write_bytes(b"mp4")
        return {**cv.parse_script(SCRIPT), "path": path, "missing_pictures": 0}

    async def say(text, kind):
        announced.append(text)
    monkeypatch.setattr(cv, "make", fake_make)
    creator._ctx.update(client=object(), announce=say)
    asyncio.run(creator.make_in_background(s, [("lowkey.lore", "a ghost", None)]))
    v = cs.load(s)["videos"][-1]
    assert v["status"] == "ready" and v["title"] == "The Last Voicemail" and v["file"].endswith("TikTok/lowkey.lore/Clip.mp4")
    assert "ready for you to approve" in announced[0]
    shown = studio(s, action="studio")
    assert "1 video waiting" in shown and shown.card["kind"] == "creator-studio"
    assert shown.card["data"]["videos"][0]["src"].startswith("/screen/file?path=")


def test_a_failed_video_is_reported_and_retried_only_a_few_times(s, monkeypatch):
    async def broken(*a, **k):
        raise RuntimeError("ffmpeg failed")
    monkeypatch.setattr(cv, "make", broken)
    creator._ctx.update(client=object())
    asyncio.run(creator.make_in_background(s, [("lowkey.lore", "", None)]))
    assert cs.load(s)["videos"][-1]["status"] == "failed"
    today = date.today()
    assert len(creator.todays_jobs(s, cs.load(s), today)) == 12  # 4 accounts x 3, the failure doesn't count
    for _ in range(2):
        asyncio.run(creator.make_in_background(s, [("lowkey.lore", "", None)]))
    assert [j[0] for j in creator.todays_jobs(s, cs.load(s), today)].count("lowkey.lore") == 0


def test_daily_quota_counts_todays_videos(s):
    add_video(s)
    add_video(s, status="posted")
    jobs = creator.todays_jobs(s, cs.load(s), date.today())
    assert [j[0] for j in jobs].count("lowkey.lore") == 1 and len(jobs) == 10  # n3on.vault's Kick needs no keys


# ---- approving -------------------------------------------------------------------------------------------

def test_approve_without_tiktok_saves_it_to_upload_by_hand(s):
    v = add_video(s)
    said = studio(s, action="approve", video="latest")
    assert "ready to upload" in said and "TIKTOK_CLIENT_KEY" in said
    assert cs.load(s)["videos"][-1]["status"] == "approved"
    with pytest.raises(ValueError):
        studio(s, action="approve", video=v["id"])
    add_video(s, title="Another Voicemail")
    assert "Rejected" in studio(s, action="skip", video="another")  # skip is an X now


def fake_tiktok(calls, views=None):
    def handler(request: httpx.Request):
        calls.append(request)
        path = request.url.path
        if path.endswith("/oauth/token/"):
            return httpx.Response(200, json={"access_token": "new", "refresh_token": "r2", "expires_in": 86400,
                                             "refresh_expires_in": 31536000, "open_id": "o"})
        if path.endswith("/creator_info/query/"):
            return httpx.Response(200, json={"data": {"privacy_level_options": ["SELF_ONLY"]}, "error": {"code": "ok"}})
        if path.endswith("/video/init/"):
            return httpx.Response(200, json={"data": {"publish_id": "p1", "upload_url": "https://up.tiktok/x"},
                                             "error": {"code": "ok"}})
        if path.endswith("/video/list/"):
            return httpx.Response(200, json={"data": {"videos": views or [], "has_more": False}, "error": {"code": "ok"}})
        if request.url.host == "up.tiktok":
            return httpx.Response(201)
        return httpx.Response(404)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def connect(s, account="lowkey.lore", expired=False):
    tiktok.save_tokens(s, {account: {"access_token": "tok", "refresh_token": "r", "expires_at": time.time() - 5 if expired else time.time() + 999,
                                     "refresh_expires_at": time.time() + 9999}})


@pytest.mark.parametrize("mode", ["draft", "direct"])
def test_approve_posts_to_tiktok(s, mode):
    s = replace(s, tiktok_client_key="k", tiktok_client_secret="sec", tiktok_mode=mode)
    connect(s, expired=True)
    add_video(s)
    calls = []
    creator._ctx["http"] = fake_tiktok(calls)
    said = asyncio.run(creator.approve(s, "latest"))
    v = cs.load(s)["videos"][-1]
    assert v["status"] == "posted" and v["publish_id"] == "p1" and v["mode"] == mode
    paths = [c.url.path for c in calls]
    assert paths[0].endswith("/oauth/token/")  # the old token was refreshed first
    upload = calls[-1]
    assert upload.headers["content-range"] == "bytes 0-999/1000" and upload.headers["content-type"] == "video/mp4"
    if mode == "draft":
        assert "/post/publish/inbox/video/init/" in paths[1] and "inbox" in said
    else:
        init = json.loads(calls[2].content)
        assert init["post_info"]["privacy_level"] == "SELF_ONLY" and init["post_info"]["is_aigc"] is True
        assert "Would you listen?" in init["post_info"]["title"] and "#story" in init["post_info"]["title"]


def test_tiktok_login_link_uses_pkce_and_remembers_the_account(s):
    with pytest.raises(ValueError):
        tiktok.login_url(s, "lowkey.lore")
    s = replace(s, tiktok_client_key="k", tiktok_client_secret="sec")
    q = parse_qs(urlparse(tiktok.login_url(s, "lowkey.lore")).query)
    assert q["redirect_uri"] == ["http://localhost:8340/tiktok/callback"] and "video.upload" in q["scope"][0]
    calls = []
    name = asyncio.run(tiktok.finish_login(fake_tiktok(calls), s, q["state"][0], "code1"))
    assert name == "lowkey.lore" and tiktok.connected(s, "lowkey.lore")
    sent = parse_qs(calls[0].content.decode())
    assert len(sent["code_verifier"][0]) > 40 and sent["code"] == ["code1"]
    with pytest.raises(ValueError):  # a login state works once
        asyncio.run(tiktok.finish_login(fake_tiktok([]), s, q["state"][0], "code1"))


def test_big_videos_upload_in_chunks():
    assert tiktok.chunks(5_000_000) == (5_000_000, 1)
    assert tiktok.chunks(100 * 1024 * 1024) == (10 * 1024 * 1024, 10)


# ---- sequels ---------------------------------------------------------------------------------------------

def test_sequels_follow_the_view_thresholds(s):
    first = add_video(s, status="posted")
    assert creator.sequels_due(cs.load(s)) == []
    assert "Part 2 comes at 50,000" in studio(s, action="set_views", video=first["id"], views="49k")
    assert "earns part 2" in studio(s, action="set_views", video=first["id"], views="80k")
    due = creator.sequels_due(cs.load(s))
    assert [d["id"] for d in due] == [first["id"]]
    idea = creator.sequel_idea(cs.load(s), due[0])
    assert "PART 2" in idea and "The Last Voicemail" in idea
    part2 = add_video(s, status="posted", part=2, series_of=first["id"], title="Voicemail 2")
    assert creator.sequels_due(cs.load(s)) == []  # part 3 needs 150k
    studio(s, action="set_views", video=part2["id"], views="150,000")
    assert [d["id"] for d in creator.sequels_due(cs.load(s))] == [part2["id"]]
    assert creator.views_needed(4) == 350_000
    part4 = add_video(s, status="posted", part=4, series_of=first["id"], title="Voicemail 4")
    studio(s, action="set_views", video=part4["id"], views="1m")
    last = creator.sequel_idea(cs.load(s), creator.sequels_due(cs.load(s))[0])
    assert "FINAL part" in last and "shocking cliffhanger" in last
    add_video(s, status="posted", part=5, series_of=first["id"], title="Voicemail 5", views=2_000_000)
    assert creator.sequels_due(cs.load(s)) == []


def test_views_are_read_from_tiktok(s):
    s = replace(s, tiktok_client_key="k", tiktok_client_secret="sec")
    connect(s)
    add_video(s, status="posted", caption="Would you listen to it again?")
    creator._ctx["http"] = fake_tiktok([], views=[{"id": "7", "video_description": "Would you listen to it again? #story",
                                                   "view_count": 64000}])
    asyncio.run(creator.refresh_views(s))
    v = cs.load(s)["videos"][-1]
    assert v["views"] == 64000 and v["post_id"] == "7"


# ---- money research ----------------------------------------------------------------------------------------

def money(s, **a):
    return money_research.run_tool("money_research", a, s)


def test_research_asks_alfred_to_search_and_save(s):
    said = money(s, action="research", topic="side hustles", budget="£100", hours="5")
    assert "web_search" in said and "save_report" in said and "£100" in said


def test_saved_research_is_downloadable(s):
    report = "## Options\n\n| Idea | Cost |\n|---|---|\n| **Faceless TikTok** | £0 |\n\n- Start today\n\n" \
             "<script>alert(1)</script>\n\n[TikTok rewards](https://www.tiktok.com/creators)"
    shown = money(s, action="save_report", title="Side hustles for 2026", report=report)
    folder = Path(s.memory_dir) / "Work" / "Money Research"
    md, page = sorted(folder.glob("*.md"))[0], sorted(folder.glob("*.html"))[0]
    assert "Faceless TikTok" in md.read_text(encoding="utf-8")
    body = page.read_text(encoding="utf-8")
    assert "<b>Faceless TikTok</b>" in body and "<script>" not in body and 'href="https://www.tiktok.com/creators"' in body
    downloads = [b for b in shown.card["buttons"] if "download" in b]
    assert len(downloads) == 2 and all(b["download"].startswith("/screen/file?path=Work/Money%20Research/") for b in downloads)
    assert "Side hustles" in money(s, action="reports").card["items"][0]["label"]


def test_money_ideas_board(s):
    money(s, action="add_idea", idea="Faceless TikTok", start_cost=0, hours="5")
    money(s, action="log_income", idea="faceless", amount=12.5)
    shown = money(s, action="ideas")
    assert shown.card["rows"][0] == ["Faceless TikTok", "earning", "£0.00", "5", "£12.50"]
    assert "£12.50 earned" in shown
    with pytest.raises(ValueError):
        money(s, action="update_idea", idea="faceless", status="rich")


def test_download_buttons_only_point_at_memory_files():
    card = screen.card("text", "x", buttons=[{"label": "Get", "download": "/screen/file?path=a.md"},
                                             {"label": "Bad", "download": "https://evil.example/x"}])
    assert card["buttons"] == [{"label": "Get", "download": "/screen/file?path=a.md"}]


def test_both_abilities_are_registered():
    assert creator in tools.ABILITIES and money_research in tools.ABILITIES


def test_studio_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    from fastapi.testclient import TestClient
    import server

    s = Settings(memory_dir=str(tmp_path / "m"), password="", creator_daily=False)
    monkeypatch.setattr(server, "settings", s)
    v = add_video(s)
    with TestClient(server.app) as client:
        assert client.post(f"/creator/videos/{v['id']}/approve").status_code == 403
        ok = client.post(f"/creator/videos/{v['id']}/approve", headers={"origin": "http://testserver"}).json()
        assert "ready to upload" in ok["said"] and ok["card"]["kind"] == "creator-studio"
        got = client.get(f"/screen/file?path={v['file']}&download=1")
        assert "attachment" in got.headers["content-disposition"]
        assert "TIKTOK_CLIENT_KEY" in client.get("/tiktok/connect?account=lowkey.lore").text


class FakeClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        text, stop = self.replies.pop(0)
        block = type("B", (), {"type": "text", "text": text})()
        return type("R", (), {"content": [block], "stop_reason": stop})()


def test_trends_are_checked_daily_and_fed_into_the_script(s):
    client = FakeClient([("", "pause_turn"), ("Trending: POV hooks, #storytime, part series.", "end_turn"),
                         (SCRIPT, "end_turn")])
    creator._ctx["client"] = client
    shown = studio(s, action="trends", account="lowkey.lore")
    assert "POV hooks" in shown.card["text"] and client.calls[0]["tools"][0]["name"] == "web_search"
    assert len(client.calls) == 2  # carried on after the pause
    studio(s, action="trends", account="lowkey.lore")
    assert len(client.calls) == 2  # once a day
    add_video(s, status="posted", views=82000)
    account = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.write_script(client, s, account, recent=["Old one"], best=creator.best_titles(cs.load(s), "lowkey.lore")))
    prompt = client.calls[2]["messages"][0]["content"]
    assert "POV hooks" in prompt and "The Last Voicemail (82,000 views)" in prompt and "Old one" in prompt


# ---- clip accounts (Clipzz) -------------------------------------------------------------------------------

import tiktokstudio_clips as clips  # noqa: E402
import twitch  # noqa: E402


def clip(i, name="kai", seconds=30.0, views=1000):
    return {"id": f"c{i}", "broadcaster_name": name, "duration": seconds, "view_count": views,
            "title": f"clip {i}", "url": f"https://clips.twitch.tv/c{i}"}


def test_pick_fills_a_minute_from_the_top_streamer_first():
    found = [clip(1, "kai", 30, 900), clip(2, "ish", 50, 800), clip(3, "kai", 20, 700), clip(4, "kai", 15, 600)]
    chosen = clips.pick(found, set())
    assert [c["id"] for c in chosen] == ["c1", "c3", "c4"] and sum(c["duration"] for c in chosen) >= 61
    assert [c["id"] for c in clips.pick(found, {"c1", "c3"})] == ["c2", "c4"]  # topped up from another streamer
    assert clips.pick([clip(1, seconds=20)], set()) == []  # can't reach a minute


def test_twitch_top_clips_uses_the_official_api(s):
    s = replace(s, twitch_client_id="id", twitch_client_secret="sec")
    twitch._token.update(value="", until=0)
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.host == "id.twitch.tv":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        if request.url.path.endswith("/games"):
            return httpx.Response(200, json={"data": [{"id": "509658"}]})
        return httpx.Response(200, json={"data": [clip(1, views=5), clip(2, views=50)]})
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    found = asyncio.run(twitch.top_clips(http, s, "new"))
    assert [c["id"] for c in found] == ["c2", "c1"]
    last = seen[-1]
    assert last.headers["client-id"] == "id" and last.headers["authorization"] == "Bearer t"
    assert last.url.params["game_id"] == "509658" and "started_at" in last.url.params


def test_old_viral_is_a_week_in_the_past():
    start, end = twitch.window("old")
    assert (end - start).days == 7 and (twitch.window("new")[1] - start).days >= 30


def allow(s, account, *names, platform="twitch", ok=True):
    data = cs.load(s)
    cs.account(data, account)["streamers"] = [{"name": n, "platform": platform, "allows_clipping": ok} for n in names]
    cs.save(s, data)


def test_clipzz_makes_a_credited_portrait_video(s, monkeypatch):
    s = replace(s, twitch_client_id="id", twitch_client_secret="sec")
    allow(s, "Clipzz", "kai")

    async def fake_top(http, settings, era, streamers, category):
        return [clip(1, "kai", 40, 900), clip(2, "kai", 30, 800)]
    monkeypatch.setattr(twitch, "top_clips", fake_top)
    monkeypatch.setattr(clips, "download", lambda url, target: (target.with_suffix(".mp4").write_bytes(b"c"), target.with_suffix(".mp4"))[1])
    made = []
    monkeypatch.setattr(clips, "portrait", lambda source, layer, out: (made.append(layer), out.write_bytes(b"p")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    creator._ctx.update(client=object())
    asyncio.run(creator.make_in_background(s, [("Clipzz", "", None)]))
    v = cs.load(s)["videos"][-1]
    assert v["status"] == "ready" and "kai" in v["caption"] and "credit" in v["caption"] and "twitch" in v["hashtags"]
    assert v["keyword"] == "new" and len(made) == 2
    assert cs.account(cs.load(s), "Clipzz")["used_clips"] == ["c1", "c2"]
    asyncio.run(creator.make_in_background(s, [("Clipzz", "", None)]))
    assert cs.load(s)["videos"][-1]["status"] == "failed"  # the same clips are never used twice
    assert creator.sequels_due(cs.load(s)) == []


def test_clipzz_waits_for_twitch_keys(s):
    jobs = creator.todays_jobs(s, cs.load(s), date.today())
    assert "Clipzz" not in [j[0] for j in jobs]
    assert "allow clipping" in creator.studio_card(s, cs.load(s))["data"]["setup"]
    allow(s, "Clipzz", "kai")
    assert "Clipzz" not in [j[0] for j in creator.todays_jobs(s, cs.load(s), date.today())]
    assert "TWITCH_CLIENT_ID" in creator.studio_card(s, cs.load(s))["data"]["setup"]
    s2 = replace(s, twitch_client_id="id", twitch_client_secret="sec")
    assert [j[0] for j in creator.todays_jobs(s2, cs.load(s2), date.today())].count("Clipzz") == 5


def test_overlay_is_a_see_through_phone_layer():
    im = clips.overlay("He did NOT expect that", "twitch.tv/kai")
    assert im.size == (cv.W, cv.H) and im.mode == "RGBA" and im.getpixel((540, 1000))[3] == 0


# ---- storytelling and quality -------------------------------------------------------------------------------

EDITED = json.dumps({"title": "The Last Voicemail", "hook": "It knew her name.", "character": "", "score": 9,
                     "scores": {"hook": 6}, "caption": "Would you?", "hashtags": ["story"],
                     "scenes": [{"text": "Play.", "narration": "At 3 a.m. she pressed play.", "picture": "a phone",
                                 "closeup": "her thumb on the screen"},
                                {"text": "Her name.", "narration": "It said her name.", "picture": "a kitchen"}]})


def test_the_writer_pitches_ideas_and_an_editor_rewrites_the_draft(s):
    draft = json.dumps({**json.loads(SCRIPT), "character": "a woman of 30, red coat", "pitches": [{"idea": "x", "score": 7}]})
    client = FakeClient([(draft, "end_turn"), (EDITED, "end_turn")])
    account = cs.load(s)["accounts"][0]
    out = asyncio.run(cv.write_script(client, s, account))
    first, second = (c["messages"][0]["content"] for c in client.calls[:2])
    assert "pitch 5 wildly different ideas" in first and "loops back" in first and '"closeup"' in first
    assert "toughest short-form story editor" in second and "The Last Voicemail" in second and first in second
    assert out["hook"] == "It knew her name." and out["score"] == 9
    assert out["character"] == "a woman of 30, red coat"  # the editor dropped it, the draft's is kept
    assert out["scenes"][0]["closeup"] == "her thumb on the screen" and out["scenes"][1]["closeup"] == ""


def test_a_failed_edit_keeps_the_draft(s):
    client = FakeClient([(SCRIPT, "end_turn"), ("not json at all", "end_turn")])
    out = asyncio.run(cv.write_script(client, s, cs.load(s)["accounts"][0]))
    assert out["title"] == "The Last Voicemail" and out["score"] == 0 and len(client.calls) == 3  # writer, editor, hook test


def test_the_hook_test_swaps_in_a_stronger_first_line(s):
    hooks = json.dumps({"hooks": [{"line": "She got a voicemail from her own phone.", "score": 9},
                                  {"line": "Meh.", "score": 4}], "current": 6})
    client = FakeClient([(SCRIPT, "end_turn"), ("no", "end_turn"), (hooks, "end_turn")])
    out = asyncio.run(cv.write_script(client, s, cs.load(s)["accounts"][0]))
    assert "8 alternative first lines" in client.calls[2]["messages"][0]["content"]
    assert out["scenes"][0]["narration"] == out["hook"] == "She got a voicemail from her own phone."
    assert out["hook_score"] == 9 and out["old_hook"] and len(out["scenes"]) == len(json.loads(SCRIPT)["scenes"])
    weaker = json.dumps({"hooks": [{"line": "Meh.", "score": 4}], "current": 8})
    kept = asyncio.run(cv.pick_hook(FakeClient([(weaker, "end_turn")]), s, cv.parse_script(SCRIPT)))
    assert kept["scenes"][0] == cv.parse_script(SCRIPT)["scenes"][0] and kept["hook_score"] == 8


def test_word_by_word_captions(tmp_path):
    words = cv.estimate_words("At three, she pressed play on it.", 3.0)
    assert words[0][0] == pytest.approx(0.1) and words[-1][1] == pytest.approx(3.0)
    assert [[w[2] for w in line] for line in cv.chunks(words)] == [["At", "three,"], ["she", "pressed", "play"], ["on", "it."]]
    listing = cv.caption_track(words, 5.0, (232, 197, 71), tmp_path, "cap0")
    text = listing.read_text()
    assert text.count("duration") == len(words) + 2  # one per word, plus the quiet lead-in and tail
    total = sum(float(line.split()[1]) for line in text.splitlines() if line.startswith("duration"))
    assert total == pytest.approx(5.0, abs=0.01)
    im = cv.caption_image(["pressed", "play"], 1, (232, 197, 71))
    assert im.size == (cv.W, cv.CAPTION_H) and im.mode == "RGBA"
    assert cv.caption_track([], 5.0, (0, 0, 0), tmp_path, "cap1") is None
    assert cv.captions_on({"style": "noir"}) and not cv.captions_on({"style": "drama"})
    assert not cv.captions_on({"style": "noir", "captions": False})


def test_a_backing_track_is_picked_from_the_music_folders(tmp_path):
    folder = tmp_path / "TikTok" / "lowkey.lore"
    folder.mkdir(parents=True)
    assert cv.music_for(folder) is None
    (tmp_path / "TikTok" / "Music").mkdir()
    (tmp_path / "TikTok" / "Music" / "all.mp3").write_bytes(b"x")
    (tmp_path / "TikTok" / "Music" / "notes.txt").write_text("x")
    assert cv.music_for(folder).name == "all.mp3"
    (folder / "Music").mkdir()
    (folder / "Music" / "mine.m4a").write_bytes(b"x")
    assert cv.music_for(folder).name == "mine.m4a"  # the account's own music comes first
    (folder / "Music" / "tense").mkdir()
    (folder / "Music" / "tense" / "strings.mp3").write_bytes(b"x")
    (folder / "Music" / "eerie piano.mp3").write_bytes(b"x")
    assert cv.music_for(folder, "tense slow build").name == "strings.mp3"  # a mood subfolder
    assert cv.music_for(folder, "Eerie ambient").name == "eerie piano.mp3"  # a mood word in the name
    parsed = cv.parse_script(json.dumps({**json.loads(SCRIPT), "mood": "eerie ambient", "sound": "Oblivion by Grimes"}))
    assert parsed["mood"] == "eerie ambient" and parsed["sound"] == "Oblivion by Grimes"


def test_the_story_bible_keeps_the_world_consistent(s):
    account = cs.new_account("lowkey.lore")
    assert "start the account's world" in cs.bible_summary(account)
    cs.update_bible(account, {"world": "A seaside town where old phones still ring.",
                              "characters": [{"name": "Mara", "look": "30, red coat, short black hair"}],
                              "threads_opened": ["Who left the voicemail?", "Why 3 a.m.?"]})
    cs.update_bible(account, {"characters": [{"name": "mara", "notes": "hears her own voice"}, {"name": "Theo", "look": "old man"}],
                              "threads_closed": ["why 3 a.m.?"], "threads_opened": ["Who left the voicemail?"]})
    bible = account["bible"]
    assert [c["name"] for c in bible["characters"]] == ["Mara", "Theo"]
    assert bible["characters"][0] == {"name": "Mara", "look": "30, red coat, short black hair", "notes": "hears her own voice"}
    assert bible["threads"] == ["Who left the voicemail?"]
    summary = cs.bible_summary(account)
    assert "seaside town" in summary and "Character Mara: 30, red coat" in summary and "Who left the voicemail?" in summary
    cs.update_bible(account, "nonsense")  # a bad update changes nothing
    assert account["bible"] == bible
    client = FakeClient([(SCRIPT, "end_turn"), (SCRIPT, "end_turn")])
    asyncio.run(cv.write_script(client, s, account))
    assert "Character Mara: 30, red coat" in client.calls[0]["messages"][0]["content"]
    assert "Story bible: @lowkey.lore" in str(studio(s, action="bible", account="lowkey.lore").card)


def test_lessons_from_view_counts_feed_the_writer(s):
    client = FakeClient([("Open on a named person mid-action: top 3 all did.", "end_turn")])
    creator._ctx["client"] = client
    try:
        for n in range(3):
            add_video(s, status="posted", views=1000 * (n + 1), title=f"V{n}")
        assert "Only 3" in studio(s, action="lessons", account="lowkey.lore").card["text"]
        assert client.calls == []  # too few videos with views to learn from
        add_video(s, status="posted", views=90000, title="Big one", hook="Maya had 9 seconds.", mood="tense")
        shown = studio(s, action="lessons", account="lowkey.lore")
        assert "mid-action" in shown.card["text"]
        rows = client.calls[0]["messages"][0]["content"]
        assert rows.index("90000 | Big one | Maya had 9 seconds. | tense") < rows.index("3000 | V2")
        asyncio.run(creator.ensure_lessons(s, "lowkey.lore"))
        assert len(client.calls) == 1  # once a day
        account = cs.account(cs.load(s), "lowkey.lore")
        prompt = cv.SCRIPT_PROMPT.format(**{k: "" for k in ("taste", "bible", "name", "theme", "format", "series",
                                         "look", "recent", "best", "trends", "idea", "variety")}, lessons=account["lessons"]["brief"])
        assert "view counts say works (follow these lessons): Open on a named person" in prompt
    finally:
        creator._ctx["client"] = None


def test_hook_text_on_the_first_scene_and_cover():
    from PIL import Image
    plain = Image.new("RGB", (cv.W, cv.H), (40, 40, 40))
    marked = cv.with_hook_text(plain, "She never called back", "#e8c547", "cinematic")
    assert marked.getpixel((cv.W // 2, 900)) == plain.getpixel((cv.W // 2, 900))  # the middle is untouched
    top = marked.crop((0, cv.HOOK_TEXT_Y, cv.W, cv.HOOK_TEXT_Y + 200)).getcolors(1 << 20)
    assert any(c[:3] == (255, 255, 255) for _, c in top)  # big white words at the top
    assert cv.with_hook_text(plain, "", "#e8c547") is plain
    assert cv.with_hook_text(plain, "Words", "#e8c547", "explainer") is plain  # it has its own headline
    parsed = cv.parse_script(json.dumps({**json.loads(SCRIPT), "cover": "She never called back"}))
    assert parsed["cover"] == "She never called back"


def test_each_scene_is_read_at_its_own_pace(s, tmp_path, monkeypatch):
    import sys
    import types
    rates = []

    class Talk:
        def __init__(self, text, name, rate="+0%", boundary=None):
            rates.append(rate)

        async def stream(self):
            yield {"type": "audio", "data": b"mp3"}
    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=Talk))
    for pace in ("slow", "fast", "shouty"):
        assert asyncio.run(cv.narrate(None, s, "Run.", "", tmp_path / f"{pace}.mp3", [], pace))
    assert rates == ["-6%", "+16%", "+6%"]
    scenes = [{"narration": "It was quiet.", "pace": "SLOW"}, {"narration": "Run!", "pace": "sprint"}]
    parsed = cv.parse_script(json.dumps({**json.loads(SCRIPT), "scenes": scenes}))
    assert [sc["pace"] for sc in parsed["scenes"]] == ["slow", "normal"]


def test_missing_pictures_are_retried_then_filled_from_other_shots():
    from PIL import Image
    a, b = Image.new("RGB", (64, 64), (200, 0, 0)), Image.new("RGB", (64, 64), (0, 0, 200))
    pictures, closeups = cv.fill_gaps([a, None, None, None], [None, b, None, None])
    assert pictures[1] is b and closeups[1] is None  # its own close-up steps in
    assert pictures[2] is not None and pictures[2].getpixel((5, 5)) == (0, 0, 200)  # the nearest scene, mirrored
    assert all(p is not None for p in pictures)
    assert cv.fill_gaps([None, None], [None, None]) == ([None, None], [None, None])  # nothing to borrow


def test_a_failed_picture_is_fetched_again(s, tmp_path, monkeypatch):
    from PIL import Image
    seeds = []

    async def flaky(http, description, style, seed, size=(1024, 1024)):
        seeds.append(seed)
        return Image.new("RGB", (64, 64)) if len(seeds) > 2 else None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", flaky)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    out = asyncio.run(cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=cv.parse_script(SCRIPT)))
    assert out["missing_pictures"] == 0 and len(seeds) == 4 and seeds[2] == seeds[0] + 13


def test_a_character_line_is_spoken_in_the_characters_voice(s, tmp_path, monkeypatch):
    voices = []

    async def no_picture(*a, **k):
        return None

    async def narrate(http, settings, text, voice, target, words=None, pace="normal"):
        voices.append(voice)
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", narrate)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    scenes = [{"narration": "The phone buzzed.", "speaker": "Narrator"},
              {"narration": "Don't open the door.", "speaker": "Old Man"}, {"narration": "Run.", "speaker": "alien"}]
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "scenes": scenes}))
    assert [sc["speaker"] for sc in script["scenes"]] == ["narrator", "old man", "alien"]  # unknown names: narrator voice
    account = {**cs.load(s)["accounts"][0], "voice": "en-GB-RyanNeural"}
    asyncio.run(cv.make(None, None, s, account, tmp_path, script=script))
    assert voices == ["en-GB-RyanNeural", cv.SPEAKERS["old man"], "en-GB-RyanNeural"]


def test_sequels_wear_a_part_badge_and_notes_carry_a_pinned_comment(s, tmp_path, monkeypatch):
    from PIL import Image
    plain = Image.new("RGB", (cv.W, cv.H), (40, 40, 40))
    assert cv.with_part_badge(plain, 1, "#e8c547") is plain
    badged = cv.with_part_badge(plain, 3, "#e8c547")
    assert badged.getpixel((70, 70)) == (232, 197, 71) and badged.getpixel((cv.W // 2, 900)) == (40, 40, 40)

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "pinned_comment": "Who left the voicemail?"}))
    out = asyncio.run(cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=script, part=2))
    assert "Pin this comment: Who left the voicemail?" in out["path"].with_suffix(".md").read_text()
    cover = Image.open(out["path"].with_suffix(".png"))
    assert cover.getpixel((70, 70)) != cover.getpixel((cv.W - 70, 70))  # the badge sits top left


def test_a_quiet_room_tone_goes_under_the_story(s, tmp_path, monkeypatch):
    calls = []

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "add_ambience", lambda video, kind, out: (calls.append(kind), out.write_bytes(b"amb")))
    assert cv.parse_script(json.dumps({**json.loads(SCRIPT), "ambience": "Thunder"}))["ambience"] == ""
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "ambience": "Rain"}))
    account = cs.load(s)["accounts"][0]
    out = asyncio.run(cv.make(None, None, s, account, tmp_path, script=script))
    assert calls == ["rain"] and out["path"].read_bytes() == b"amb"
    asyncio.run(cv.make(None, None, s, {**account, "ambience": False}, tmp_path, script=script))
    assert calls == ["rain"]  # an account can turn it off


def test_variety_brief_steers_the_next_video_away_from_the_last_ones(s):
    add_video(s, status="posted", title="Old", mood="cosy", hook="Old hook.")
    add_video(s, status="rejected", title="Binned", mood="sad")
    add_video(s, status="ready", title="The Last Voicemail", mood="tense", hook="Maya had 9 seconds.", story="Maya stares at the phone.")
    brief = creator.variety_brief(cs.load(s), "lowkey.lore", count=2)
    assert "Binned" not in brief and '"Old"' in brief
    assert 'mood tense, opened with "Maya had 9 seconds.", began: Maya stares' in brief
    assert creator.variety_brief(cs.load(s), "nobody") == ""
    client = FakeClient([(SCRIPT, "end_turn"), (SCRIPT, "end_turn")])
    asyncio.run(cv.write_script(client, s, cs.account(cs.load(s), "lowkey.lore"), variety=brief))
    assert "make today's clearly different" in client.calls[0]["messages"][0]["content"]
    assert "Maya had 9 seconds." in client.calls[0]["messages"][0]["content"]


def test_named_characters_keep_their_voice_across_videos(s, tmp_path, monkeypatch):
    voices = []

    async def no_picture(*a, **k):
        return None

    async def narrate(http, settings, text, voice, target, words=None, pace="normal"):
        voices.append(voice)
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", narrate)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    account = {**cs.load(s)["accounts"][0], "voice": "en-GB-RyanNeural"}
    bible = {"characters": [{"name": "Mara", "look": "30, red coat", "voice_type": "woman"},
                            {"name": "Theo", "look": "old", "voice_type": "old man"}]}
    scenes = [{"narration": "The phone buzzed.", "speaker": "narrator"}, {"narration": "Who is this?", "speaker": "Mara"},
              {"narration": "Stay inside.", "speaker": "Theo"}]
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "scenes": scenes, "bible": bible}))
    result = asyncio.run(cv.make(None, None, s, account, tmp_path, script=script))
    mara, theo = voices[1], voices[2]
    assert mara in cs.CHARACTER_VOICES["woman"] and theo in cs.CHARACTER_VOICES["old man"] and voices[0] == "en-GB-RyanNeural"
    cs.update_bible(account, result["bible"])
    assert {c["name"]: c["voice"] for c in account["bible"]["characters"]} == {"Mara": mara, "Theo": theo}
    assert "Character Mara: 30, red coat [voice: woman]" in cs.bible_summary(account)
    # a later video: Mara comes back without a voice type and sounds the same; a second woman gets a different voice
    voices.clear()
    later = {"characters": [{"name": "mara"}, {"name": "June", "voice_type": "woman"}]}
    scenes = [{"narration": "It's me again.", "speaker": "Mara"}, {"narration": "Hello?", "speaker": "June"}]
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "scenes": scenes, "bible": later}))
    asyncio.run(cv.make(None, None, s, account, tmp_path, script=script))
    assert voices[0] == mara and voices[1] in cs.CHARACTER_VOICES["woman"] and voices[1] != mara
    cs.update_bible(account, {"characters": [{"name": "Mara", "voice": "en-US-JennyNeural"}]})
    assert {c["name"]: c["voice"] for c in account["bible"]["characters"]}["Mara"] == mara  # a voice, once given, never changes


def test_retention_pass_rewrites_the_scene_viewers_would_swipe_on(s):
    base = json.loads(SCRIPT)
    scenes = [{"text": f"Line {i}", "narration": f"Scene {i} happens.", "picture": f"shot {i}"} for i in range(1, 6)]
    script = cv.parse_script(json.dumps({**base, "scenes": scenes}))
    n = len(script["scenes"])
    weak = {"scores": [8] + [3] + [7] * (n - 3), "weakest": 3, "why": "a summary, nothing new",
            "text": "The voicemail was from tomorrow", "narration": "The timestamp said tomorrow.", "after": 9}
    fixed = asyncio.run(cv.fix_retention(FakeClient([(json.dumps(weak), "end_turn")]), s, script))
    assert fixed["scenes"][2]["narration"] == "The timestamp said tomorrow."
    assert fixed["scenes"][2]["picture"] == script["scenes"][2]["picture"]  # same shot, sharper line
    assert fixed["scenes"][1] == script["scenes"][1] and len(fixed["scenes"]) == n
    assert fixed["retention"] == 7 and "scene 3 rewritten (3 to 9/10)" in fixed["retention_fix"]
    # a rewrite that isn't better, a hook scene, or a broken reply: the script stands
    worse = {**weak, "after": 2}
    kept = asyncio.run(cv.fix_retention(FakeClient([(json.dumps(worse), "end_turn")]), s, script))
    assert kept["scenes"] == script["scenes"] and "retention_fix" not in kept
    hook = {**weak, "weakest": 1}
    assert asyncio.run(cv.fix_retention(FakeClient([(json.dumps(hook), "end_turn")]), s, script))["scenes"] == script["scenes"]
    assert asyncio.run(cv.fix_retention(FakeClient([("no json", "end_turn")]), s, script)) == script
    assert asyncio.run(cv.fix_retention(FakeClient([]), s, script)) == script
