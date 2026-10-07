from types import SimpleNamespace
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

@pytest.fixture(autouse=True)
def clip_pages(monkeypatch):
    """The clip pages were retired (7 Oct), but the clip code is still tested with them."""
    monkeypatch.setattr(cs, "STARTERS", cs.STARTERS + cs.CLIP_PAGES)



@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), tiktok_client_key="", tiktok_client_secret="")


@pytest.fixture(autouse=True)
def idle_studio(monkeypatch):
    creator._ctx.update(client=None, http=None, announce=None, making=False, views_at=0.0, pending=[])
    monkeypatch.setattr(cs, "SWITCH_OFF_OTHERS", False)  # these tests use every page; the switch-off has its own tests
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
    assert [a["style"] for a in data["accounts"]] == ["lore", "explainer", "drama", "clips", "clips"]
    assert [a["per_day"] for a in data["accounts"]] == [3, 3, 3, 5, 3]


def test_clip_pages_are_removed_once_from_an_older_studio(s):
    old = {"accounts": [cs.new_account(**a) for a in cs.STARTERS], "videos": [], "starters_added": ["Clipzz", "n3on.vault"]}
    (Path(s.memory_dir) / cs.FILE).write_text(json.dumps(old), encoding="utf-8")
    assert [a["name"] for a in cs.load(s)["accounts"]] == ["lowkey.lore", "mindglitch.fyi", "karma.receipts"]
    data = cs.load(s)
    data["accounts"].append(cs.new_account(**cs.CLIP_PAGES[0]))  # added back on purpose: it stays
    cs.save(s, data)
    assert [a["name"] for a in cs.load(s)["accounts"]][-1] == "Clipzz"


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
    assert shown.card["rows"][0][:2] == ["lowkey.lore", "lore"] and shown.card["rows"][0][4] == "no"


def test_delete_videos_clears_the_made_videos_but_keeps_the_lessons(s):
    v = add_video(s)
    folder = cs.work_folder(s, "TikTok", "lowkey.lore")
    (folder / "clip.png").write_bytes(b"png")
    (folder / "clip.md").write_text("notes", encoding="utf-8")
    (folder / "Profile picture.png").write_bytes(b"png")
    (folder / "lost.mp4").write_bytes(b"mp4")  # a video the studio lost track of
    other = cs.work_folder(s, "TikTok", "mindglitch.fyi")
    (other / "kept.mp4").write_bytes(b"mp4")
    making = add_video(s, status="making", file="")
    data = cs.load(s)
    cs.account(data, "lowkey.lore")["taste"]["liked"].append({"title": "Liked one"})
    cs.save(s, data)
    assert "confirm" in studio(s, action="delete_videos", account="lowkey.lore")
    assert (folder / "clip.mp4").exists()  # nothing goes without a yes
    said = studio(s, action="delete_videos", account="lowkey.lore", confirmed=True)
    assert "Deleted 2 videos for lowkey.lore" in said
    assert sorted(p.name for p in folder.iterdir()) == ["Profile picture.png"]
    assert (other / "kept.mp4").exists()  # another account's videos stay
    data = cs.load(s)
    rows = {r["id"]: r for r in data["videos"]}
    assert rows[v["id"]]["status"] == "deleted" and "file" not in rows[v["id"]]
    assert rows[making["id"]]["status"] == "making"  # the one being made is left alone
    assert cs.account(data, "lowkey.lore")["taste"]["liked"]  # the lessons stay
    assert creator.queue(s) == []
    studio(s, action="delete_videos", confirmed=True)  # every account
    assert not (other / "kept.mp4").exists()


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


def test_viral_lore_tiktoks_are_studied_every_few_days_and_steer_the_script(s, monkeypatch):
    client = FakeClient([("", "pause_turn"), ("Open on the answer, then rewind (videos with 400k likes).", "end_turn"),
                         (SCRIPT, "end_turn")])
    creator._ctx["client"] = client
    try:
        shown = studio(s, action="viral", account="lowkey.lore")
        assert "Open on the answer" in shown.card["text"] and "Make one using this" in str(shown.card)
        ask = client.calls[0]["messages"][0]["content"]
        assert "50,000 or more likes" in ask and cs.STYLES["lore"] in ask  # the account's own style
        assert client.calls[0]["tools"][0]["name"] == "web_search" and len(client.calls) == 2  # carried on after the pause
        studio(s, action="viral", account="lowkey.lore")
        assert len(client.calls) == 2  # kept for a few days, not searched every video
        account = cs.account(cs.load(s), "lowkey.lore")
        asyncio.run(cv.write_script(client, s, account))
        prompt = client.calls[2]["messages"][0]["content"]
        assert "50,000+ likes" in prompt and "Open on the answer, then rewind" in prompt
        assert "Make viewers think" in prompt and "comment their theories" in prompt
        data = cs.load(s)  # an old playbook is studied again
        cs.account(data, "lowkey.lore")["viral"]["day"] = "2000-01-01"
        cs.save(s, data)
        client.replies.append(("Fresh playbook.", "end_turn"))
        assert asyncio.run(creator.ensure_viral(s, "lowkey.lore"))["brief"] == "Fresh playbook."
        async def broken(*a, **k):
            raise RuntimeError("no web search")
        monkeypatch.setattr(cv, "study_viral", broken)  # a failed study keeps the last playbook
        assert asyncio.run(creator.ensure_viral(s, "lowkey.lore", force=True))["brief"] == "Fresh playbook."
    finally:
        creator._ctx["client"] = None


def test_a_script_without_a_viral_study_still_gets_written():
    prompt = cv.SCRIPT_PROMPT.format(**{k: "x" for k in ("taste", "bible", "name", "theme", "format", "series", "look",
                                     "recent", "best", "trends", "idea", "variety", "lessons", "viral")})
    assert "borrow the techniques, never the stories" in prompt


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


def compilation(s, account):
    """The classic clip account: joined viewer clips, no moments cut from streams."""
    data = cs.load(s)
    cs.account(data, account).update(continue_at=0, stream_min_views=0)
    cs.save(s, data)


def test_clipzz_makes_a_credited_portrait_video(s, monkeypatch):
    s = replace(s, twitch_client_id="id", twitch_client_secret="sec")
    allow(s, "Clipzz", "kai")
    compilation(s, "Clipzz")

    async def fake_top(http, settings, era, streamers, category):
        return [clip(1, "kai", 40, 900), clip(2, "kai", 30, 800)]
    monkeypatch.setattr(twitch, "top_clips", fake_top)
    monkeypatch.setattr(clips, "download", lambda url, target: (target.with_suffix(".mp4").write_bytes(b"c"), target.with_suffix(".mp4"))[1])
    made = []
    monkeypatch.setattr(clips, "portrait", lambda source, layer, out: (made.append(layer), out.write_bytes(b"p")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "check_video", lambda path: ["12 seconds of black screen"])
    monkeypatch.setattr(cv, "video_facts", lambda path: "1:02, 30.0 MB")
    creator._ctx.update(client=object())
    asyncio.run(creator.make_in_background(s, [("Clipzz", "", None)]))
    v = cs.load(s)["videos"][-1]
    assert v["checks"] == ["12 seconds of black screen"]  # watched before it's offered, like the studio's videos
    assert "Check before posting: 12 seconds of black screen" in v["notes"]
    notes = next(cs.work_folder(s, "TikTok", "Clipzz").glob("*.md")).read_text(encoding="utf-8")
    assert "Length: 1:02, 30.0 MB" in notes and "Quality check: 12 seconds of black screen" in notes
    assert v["status"] == "ready" and "kai" in v["caption"] and "credit" in v["caption"] and "twitch" in v["hashtags"]
    assert v["keyword"] == "new" and len(made) == 2
    assert cs.account(cs.load(s), "Clipzz")["used_clips"] == ["c1", "c2"]
    asyncio.run(creator.make_in_background(s, [("Clipzz", "", None)]))
    assert cs.load(s)["videos"][-1]["status"] == "failed"  # the same clips are never used twice
    assert creator.sequels_due(cs.load(s)) == []


def test_clips_from_quiet_and_loud_streamers_end_up_equally_loud(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    import re
    import subprocess
    from PIL import Image
    layer = tmp_path / "layer.png"
    Image.new("RGBA", (cv.W, cv.H), (0, 0, 0, 0)).save(layer)

    def loudness(path):
        out = subprocess.run([cv.ffmpeg(), "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])
    levels = []
    for name, volume in (("quiet", 0.02), ("loud", 0.9)):
        source = tmp_path / f"{name}.mp4"  # a 1280x720 stream clip
        subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", "testsrc=s=1280x720:d=2", "-f", "lavfi", "-i",
                        f"sine=f=330:d=2,volume={volume}", "-shortest", str(source)], check=True, capture_output=True)
        part = tmp_path / f"{name}-part.mp4"
        clips.portrait(source, layer, part)
        clips.level(part)
        levels.append(loudness(part))
    assert abs(levels[0] - levels[1]) < 2 and all(abs(v + 14) < 2 for v in levels)
    clips.level(tmp_path / "missing.mp4")  # a failure is skipped, never fatal


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
    pops = text.count("-pop.png")  # a fresh line pops in for a couple of frames first
    assert text.count("duration") - pops == len(words) + 2  # one per word, plus the quiet lead-in and tail
    assert pops >= 1
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
                                         "look", "recent", "best", "trends", "idea", "variety", "viral")}, lessons=account["lessons"]["brief"])
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
    c = Image.new("RGB", (64, 64), (0, 200, 0))
    pictures, closeups, details = cv.fill_gaps([a, None, None], [None, None, None], [None, c, None])
    assert pictures[1] is c and details[1] is None  # the scene's own detail shot beats a neighbour's crop
    assert pictures[2].getpixel((5, 5)) == (0, 200, 0)  # and can itself be borrowed by the next scene


def test_a_failed_picture_is_fetched_again(s, tmp_path, monkeypatch):
    from PIL import Image
    seeds = []

    async def flaky(http, description, style, seed, size=(1024, 1024)):
        seeds.append((description, seed))
        await asyncio.sleep(0.05 if len(seeds) == 1 else 0)  # the first scene's picture is slow to fail
        return Image.new("RGB", (64, 64)) if sum(d == description for d, _ in seeds) > 1 else None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", flaky)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    out = asyncio.run(cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=cv.parse_script(SCRIPT)))
    assert out["missing_pictures"] == 0 and len(seeds) == 4
    first, second = [[n for d, n in seeds if d == desc] for desc in dict.fromkeys(d for d, _ in seeds)]
    assert first[1] == first[0] + 13 and second[1] == second[0] + 13
    assert seeds[2][0] == seeds[1][0]  # the quick failure was retried straight away, not after the slow one


def test_a_character_line_is_spoken_in_the_characters_voice(s, tmp_path, monkeypatch):
    voices = []

    async def no_picture(*a, **k):
        return None

    async def narrate(http, settings, text, voice, target, words=None, pace="normal", narrator=""):
        voices.append(voice)
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "VOICE_TRIES", 1)  # these voices fail on purpose; count each scene once
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

    async def narrate(http, settings, text, voice, target, words=None, pace="normal", narrator=""):
        voices.append(voice)
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "VOICE_TRIES", 1)  # these voices fail on purpose; count each scene once
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


def test_last_scene_settles_into_the_first_frame_so_the_video_loops(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image, ImageChops, ImageDraw, ImageStat
    first, last = tmp_path / "first.png", tmp_path / "last.png"
    im = Image.new("RGB", (cv.W, cv.H), (20, 30, 90))
    ImageDraw.Draw(im).rectangle((300, 600, 780, 1300), fill=(240, 200, 40))
    im.save(first)
    Image.new("RGB", (cv.W, cv.H), (200, 40, 40)).save(last)
    cv.render_scene([first], None, 0.5, tmp_path / "s0.mp4", move=0)
    cv.render_scene([last], None, 0.5, tmp_path / "s9.mp4", move=3, loop_to=first)

    def frame(video, which):
        out = tmp_path / f"{video.stem}-{which}.png"
        pick = ["-vf", "select=eq(n\\,0)"] if which == "first" else ["-sseof", "-0.05"]
        args = [cv.ffmpeg(), "-y", *(pick[:2] if which == "last" else []), "-i", str(video),
                *(pick if which == "first" else []), "-frames:v", "1", str(out)]
        subprocess.run(args, check=True, capture_output=True)
        return Image.open(out).convert("RGB")
    start, end = frame(tmp_path / "s0.mp4", "first"), frame(tmp_path / "s9.mp4", "last")
    assert ImageStat.Stat(ImageChops.difference(start, end).convert("L")).mean[0] < 6  # the end frame is the opening frame
    assert cv.audio_seconds(tmp_path / "s9.mp4") > 1.2  # the settle is added on top, not cut from the scene


def test_punch_words_are_drawn_bigger_in_the_captions(tmp_path):
    script = json.loads(SCRIPT)
    script["scenes"][0]["punch"] = ["Voicemail!", "own phone", "extra"]
    assert cv.parse_script(json.dumps(script))["scenes"][0]["punch"] == ["voicemail", "own"]
    assert cv.parse_script(SCRIPT)["scenes"][0]["punch"] == []
    assert cv.punch_words("3AM, 100%") == ["3am", "100%"]
    plain = cv.caption_image(["a", "voicemail."], 0, (232, 197, 71))
    punched = cv.caption_image(["a", "voicemail."], 0, (232, 197, 71), ["voicemail"])

    def ink(im, colour):  # how many pixels are drawn in that colour
        return sum(1 for p in im.getdata() if p[3] and p[:3] == colour)
    assert ink(punched, (232, 197, 71)) > ink(plain, (232, 197, 71))  # the key word is in the accent colour, and bigger
    listing = cv.caption_track(cv.estimate_words("A voicemail.", 2.0), 2.0, (232, 197, 71), tmp_path, "p", ["voicemail"])
    assert listing and listing.exists()


def test_scene_sound_effects_are_cued_and_capped(s, tmp_path, monkeypatch):
    script = json.loads(SCRIPT)
    for scene in script["scenes"]:
        scene["hit"] = "Boom"
    script["scenes"][0]["hit"] = "kazoo"
    parsed = cv.parse_script(json.dumps(script))
    assert parsed["scenes"][0]["hit"] == "" and parsed["scenes"][1]["hit"] == "boom"
    parsed["scenes"] = parsed["scenes"] + [dict(parsed["scenes"][1]) for _ in range(4)]
    played = []

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (played.append((a[1], a[4])), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    asyncio.run(cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=parsed))
    played = [h for _, h in sorted(played)]  # scenes render side by side, so put them back in order
    assert sum(bool(h) for h in played) == cv.MAX_HITS and played[0] == ""


def test_a_sound_effect_renders_with_ffmpeg(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    from PIL import Image
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (10, 10, 10)).save(still)
    for kind in cv.HITS:
        cv.render_scene([still], None, 0.4, tmp_path / f"{kind}.mp4", hit=kind)
        assert cv.audio_seconds(tmp_path / f"{kind}.mp4") >= 0.39


def test_a_shaking_hit_renders_on_a_scene_with_several_shots(tmp_path):
    """The shake's zoom changed the first shot's pixel shape, so ffmpeg refused to join it to the next shot."""
    pytest.importorskip("imageio_ffmpeg")
    from PIL import Image
    shots = []
    for i, colour in enumerate(((200, 0, 0), (0, 0, 200), (0, 200, 0))):
        shots.append(tmp_path / f"{i}.png")
        Image.new("RGB", (cv.W, cv.H), colour).save(shots[-1])
    for kind in cv.SHAKE_HITS:
        cv.render_scene(shots[:2], None, 1.0, tmp_path / f"{kind}.mp4", hit=kind, teaser=shots[2], rewind=True)
        assert cv.audio_seconds(tmp_path / f"{kind}.mp4") >= 0.99


def test_ffmpeg_errors_show_the_cause(monkeypatch):
    class Done:
        returncode = 1
        stderr = ("[Parsed_concat_12 @ 0x1] Input link in0:v0 parameters do not match\n"
                  "[vost#0:0/libx264 @ 0x2] Task finished with error code: -22 (Invalid argument)\nConversion failed!\n")
    monkeypatch.setattr(cv.subprocess, "run", lambda *a, **k: Done())
    with pytest.raises(RuntimeError, match="Parsed_concat_12.*do not match"):
        cv.run(["-i", "x"])


def test_the_camera_follows_the_pace_and_a_boom_shakes_it(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image, ImageChops, ImageDraw, ImageStat
    still = tmp_path / "s.png"
    im = Image.new("RGB", (cv.W, cv.H), (20, 30, 90))
    ImageDraw.Draw(im).rectangle((300, 600, 780, 1300), fill=(240, 200, 40))
    im.save(still)

    def frame(video, n):
        out = tmp_path / f"{video.stem}-{n}.png"
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(video), "-vf", f"select=eq(n\\,{n})", "-frames:v", "1", str(out)],
                       check=True, capture_output=True)
        return Image.open(out).convert("L")

    def moved(a, b):
        return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]
    for name, kw in {"calm": {}, "boom": {"hit": "boom"}, "slow": {"pace": "slow"}, "fast": {"pace": "fast"}}.items():
        cv.render_scene([still], None, 1.0, tmp_path / f"{name}.mp4", **kw)
    assert moved(frame(tmp_path / "boom.mp4", 2), frame(tmp_path / "calm.mp4", 2)) > 1  # jolted off the calm frame
    assert moved(frame(tmp_path / "boom.mp4", 25), frame(tmp_path / "calm.mp4", 25)) < moved(
        frame(tmp_path / "boom.mp4", 2), frame(tmp_path / "calm.mp4", 2))  # and it settles
    slow = moved(frame(tmp_path / "slow.mp4", 0), frame(tmp_path / "slow.mp4", 29))
    fast = moved(frame(tmp_path / "fast.mp4", 0), frame(tmp_path / "fast.mp4", 29))
    assert fast > slow  # a fast scene's camera travels further in the same second


def test_scenes_are_encoded_at_the_full_frame_rate(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (10, 10, 10)).save(still)
    cv.render_scene([still], None, 1.0, tmp_path / "s.mp4")
    info = subprocess.run([cv.ffmpeg(), "-i", str(tmp_path / "s.mp4")], capture_output=True, text=True).stderr
    assert f"{cv.FPS} fps" in info  # not dropped to ffmpeg's default 25, which made the camera moves judder


def test_a_draft_script_is_read_first_then_filmed_exactly(s, monkeypatch):
    drafted = {**cv.parse_script(SCRIPT), "score": 8, "hook_score": 9}
    drafted["scenes"][1]["hit"] = "boom"
    filmed = []

    async def fake_write(client, settings, account, idea="", recent=None, best=None, taste="", variety=""):
        return drafted

    async def nothing(*a, **k):
        return None

    async def fake_make(client, http, settings, account, folder, idea="", recent=None, script=None, best=None, taste="", part=1, variety=""):
        filmed.append(script)
        path = folder / "Drafted.mp4"
        path.write_bytes(b"mp4")
        return {**script, "path": path, "missing_pictures": 0}
    monkeypatch.setattr(cv, "write_script", fake_write)
    monkeypatch.setattr(cv, "make", fake_make)
    monkeypatch.setattr(creator, "ensure_trends", nothing)
    monkeypatch.setattr(creator, "ensure_lessons", nothing)
    monkeypatch.setattr(creator, "ensure_viral", nothing)
    creator._ctx.update(client=object())
    text = asyncio.run(creator.run_tool("tiktok_studio", {"action": "draft_script", "account": "lowkey.lore"}, s))
    assert "The Last Voicemail" in text and "editor 8/10" in text and "sound: boom" in text and "film it" in text
    assert len(cs.load(s)["drafts"]) == 1 and not cs.load(s)["videos"]  # nothing filmed yet
    creator._ctx["making"] = True  # another video is being made: the draft queues behind it
    queued = asyncio.run(creator.run_tool("tiktok_studio", {"action": "make_video", "draft": "latest"}, s))
    assert "next in line" in queued and not cs.load(s).get("drafts")
    creator._ctx["making"] = False
    asyncio.run(creator.make_in_background(s, []))
    assert filmed == [drafted] and cs.load(s)["videos"][-1]["status"] == "ready"
    with pytest.raises(ValueError, match="no draft"):
        asyncio.run(creator.run_tool("tiktok_studio", {"action": "make_video", "draft": "latest"}, s))


def test_a_boom_flashes_white_and_a_glitch_splits_the_colours(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image, ImageChops, ImageDraw, ImageStat
    still = tmp_path / "s.png"
    im = Image.new("RGB", (cv.W, cv.H), (20, 30, 90))
    ImageDraw.Draw(im).rectangle((300, 600, 780, 1300), fill=(240, 200, 40))
    im.save(still)

    def frame(video, n):
        out = tmp_path / f"{video.stem}-{n}.png"
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(video), "-vf", f"select=eq(n\\,{n})", "-frames:v", "1", str(out)],
                       check=True, capture_output=True)
        return Image.open(out).convert("RGB")
    for name, kw in {"calm": {}, "boom": {"hit": "boom"}, "glitch": {"hit": "glitch"}}.items():
        cv.render_scene([still], None, 1.0, tmp_path / f"{name}.mp4", **kw)
    bright = [ImageStat.Stat(frame(tmp_path / f"{n}.mp4", 0).convert("L")).mean[0] for n in ("calm", "boom")]
    assert bright[1] > bright[0] + 60  # the boom opens on a flash
    late = ImageStat.Stat(ImageChops.difference(frame(tmp_path / "glitch.mp4", 20), frame(tmp_path / "calm.mp4", 20)))
    early = ImageStat.Stat(ImageChops.difference(frame(tmp_path / "glitch.mp4", 1), frame(tmp_path / "calm.mp4", 1)))
    assert sum(early.mean) > sum(late.mean) + 5  # the glitch only lasts a moment


def test_the_notes_give_the_videos_length_and_size(tmp_path, monkeypatch):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x" * 2_500_000)
    monkeypatch.setattr(cv, "audio_seconds", lambda path: 64.4)
    assert cv.video_facts(video) == "1:04, 2.5 MB"
    monkeypatch.setattr(cv, "audio_seconds", lambda path: 0.0)
    assert cv.video_facts(video) == "" and cv.video_facts(tmp_path / "gone.mp4") == ""


def test_a_picture_frozen_still_is_flagged_but_a_moving_one_is_not(tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    monkeypatch.setattr(cv, "MIN_LENGTH", 1.0)
    moving, stuck = tmp_path / "moving.mp4", tmp_path / "stuck.mp4"
    subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=5", "-f", "lavfi", "-i",
                    "sine=f=440:d=5", "-shortest", "-pix_fmt", "yuv420p", str(moving)], check=True, capture_output=True)
    subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", "color=c=0x7850c8:s=320x240:r=30:d=5", "-f", "lavfi", "-i",
                    "sine=f=440:d=5", "-shortest", "-pix_fmt", "yuv420p", str(stuck)], check=True, capture_output=True)
    assert cv.check_video(moving) == []
    assert any("frozen still" in p for p in cv.check_video(stuck))


def test_a_murky_dark_picture_is_flagged_but_a_bright_one_is_not(tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    monkeypatch.setattr(cv, "MIN_LENGTH", 1.0)
    monkeypatch.setattr(cv, "FREEZE_SECONDS", 60.0)
    for name, colour in (("murky", "0x1c1c1c"), ("bright", "0x7850c8")):
        subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", f"color=c={colour}:s=320x240:r=30:d=2", "-f", "lavfi",
                        "-i", "sine=f=440:d=2", "-shortest", "-pix_fmt", "yuv420p", str(tmp_path / f"{name}.mp4")],
                       check=True, capture_output=True)
    assert any("very dark" in p for p in cv.check_video(tmp_path / "murky.mp4"))
    assert cv.check_video(tmp_path / "bright.mp4") == []


def test_a_silent_opening_is_flagged_so_the_hook_lands_straight_away(tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    monkeypatch.setattr(cv, "MIN_LENGTH", 1.0)
    for name, sound in (("late", "sine=f=440:d=2,adelay=1200,apad=whole_dur=4"), ("prompt", "sine=f=440:d=4")):
        subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=4", "-f", "lavfi", "-i",
                        sound, "-t", "4", "-pix_fmt", "yuv420p", str(tmp_path / f"{name}.mp4")], check=True,
                       capture_output=True)
    late = cv.check_video(tmp_path / "late.mp4")
    assert any("first 1.2 seconds are silent" in p for p in late)
    assert not any("dead air" in p for p in late)  # a short pause isn't dead air
    assert cv.check_video(tmp_path / "prompt.mp4") == []


def test_silence_running_to_the_very_end_still_counts_as_dead_air(tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    monkeypatch.setattr(cv, "MIN_LENGTH", 1.0)
    subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=6", "-f", "lavfi", "-i",
                    "sine=f=440:d=2,apad=whole_dur=6", "-t", "6", "-pix_fmt", "yuv420p", str(tmp_path / "trail.mp4")],
                   check=True, capture_output=True)
    assert any("4 seconds of dead air" in p for p in cv.check_video(tmp_path / "trail.mp4"))


def test_the_finished_video_is_checked_before_it_is_offered(tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    from PIL import Image
    dark, lit = tmp_path / "dark.png", tmp_path / "lit.png"
    Image.new("RGB", (cv.W, cv.H), (0, 0, 0)).save(dark)
    Image.new("RGB", (cv.W, cv.H), (120, 90, 200)).save(lit)
    cv.render_scene([dark], None, 1.5, tmp_path / "dark.mp4")
    problems = cv.check_video(tmp_path / "dark.mp4")
    assert any("seconds long" in p for p in problems) and "there's no sound" in problems
    assert any("black screen" in p for p in problems)
    cv.render_scene([lit], None, 1.5, tmp_path / "lit.mp4", hit="boom")
    monkeypatch.setattr(cv, "MIN_LENGTH", 1.0)
    assert cv.check_video(tmp_path / "lit.mp4") == []  # long enough, has a sound, no black
    import subprocess
    voice = tmp_path / "pause.m4a"  # half a second of voice, then three and a half seconds of nothing
    subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", "sine=f=440:d=0.6,apad=whole_dur=4", "-c:a", "aac",
                    str(voice)], check=True, capture_output=True)
    cv.render_scene([lit], voice, 4.0, tmp_path / "pause.mp4")
    assert any("dead air" in p for p in cv.check_video(tmp_path / "pause.mp4"))


def test_check_problems_are_shown_with_the_video(s, monkeypatch):
    async def fake_make(client, http, settings, account, folder, idea="", recent=None, script=None, best=None, taste="", part=1, variety=""):
        path = folder / "Quiet.mp4"
        path.write_bytes(b"mp4")
        return {**cv.parse_script(SCRIPT), "path": path, "missing_pictures": 0, "checks": ["there's no sound"]}
    monkeypatch.setattr(cv, "make", fake_make)
    creator._ctx.update(client=object())
    asyncio.run(creator.make_in_background(s, [("lowkey.lore", "", None)]))
    v = cs.load(s)["videos"][-1]
    assert v["checks"] == ["there's no sound"] and "Check before posting: there's no sound" in v["notes"]


def test_the_mood_picks_a_colour_grade(tmp_path):
    assert cv.grade_for("tense slow piano") == "cold" and cv.grade_for("upbeat hype") == "vivid"
    assert cv.grade_for("nostalgic lo-fi") == "warm" and cv.grade_for("jazz") == ""
    assert cv.grade_for("tense", {"grade": "warm"}) == "warm" and cv.grade_for("tense", {"grade": False}) == ""
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image, ImageStat
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (128, 128, 128)).save(still)

    def mean(name, **kw):
        cv.render_scene([still], None, 0.3, tmp_path / f"{name}.mp4", **kw)
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / f"{name}.mp4"), "-frames:v", "1",
                        str(tmp_path / f"{name}.png")], check=True, capture_output=True)
        return ImageStat.Stat(Image.open(tmp_path / f"{name}.png").convert("RGB")).mean
    plain, cold, warm = mean("plain"), mean("cold", grade="cold"), mean("warm", grade="warm")
    assert cold[2] - cold[0] > plain[2] - plain[0] + 3  # bluer
    assert warm[0] - warm[2] > plain[0] - plain[2] + 3  # redder


def test_pictures_are_sharpened_after_scaling_up(tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image, ImageDraw, ImageFilter, ImageStat
    still = tmp_path / "s.png"
    im = Image.new("RGB", (cv.W, cv.H), (60, 60, 60))
    draw = ImageDraw.Draw(im)
    for x in range(0, cv.W, 12):
        draw.rectangle([x, 0, x + 5, cv.H], fill=(200, 200, 200))
    im.filter(ImageFilter.GaussianBlur(1.5)).save(still)
    monkeypatch.setattr(cv, "VIGNETTE", "")  # measured on its own, with x264's plain bit spreading so the
    monkeypatch.setattr(cv, "VIDEO_CODEC", cv.VIDEO_CODEC[:6])  # encoder's own choices don't blur the comparison

    def edges(name):
        cv.render_scene([still], None, 0.3, tmp_path / f"{name}.mp4")
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / f"{name}.mp4"), "-frames:v", "1",
                        str(tmp_path / f"{name}.png")], check=True, capture_output=True)
        return ImageStat.Stat(Image.open(tmp_path / f"{name}.png").convert("L").filter(ImageFilter.FIND_EDGES)).stddev[0]
    sharp = edges("sharp")
    monkeypatch.setattr(cv, "SHARPEN", "")
    assert sharp > edges("soft") * 1.1


def test_a_soft_vignette_darkens_the_corners(tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (160, 160, 160)).save(still)

    def frame(name):
        cv.render_scene([still], None, 0.3, tmp_path / f"{name}.mp4")
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / f"{name}.mp4"), "-frames:v", "1",
                        str(tmp_path / f"{name}.png")], check=True, capture_output=True)
        return Image.open(tmp_path / f"{name}.png").convert("L")
    shaded = frame("shaded")
    corner, middle = shaded.getpixel((20, 20)), shaded.getpixel((cv.W // 2, cv.H // 2))
    assert corner < middle - 20 and middle > 140  # dark corners, the middle left as it was
    monkeypatch.setattr(cv, "VIGNETTE", "")
    plain = frame("plain")
    assert abs(plain.getpixel((20, 20)) - plain.getpixel((cv.W // 2, cv.H // 2))) < 5


def test_captions_stay_clear_of_tiktoks_buttons_and_caption_text():
    for line, punch in ((["she", "never", "called"], ()), (["unbelievably", "extraordinary", "voicemail."], ["voicemail"])):
        im = cv.caption_image(line, 0, (232, 197, 71), punch)
        left, top, right, bottom = im.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox()  # the
        # soft shadow's faint outer fringe doesn't count, only what can actually be seen
        assert left >= cv.SAFE_SIDE - 10 and right <= cv.W - cv.SAFE_SIDE + 10  # the stroke may spill a few px
        assert cv.CAPTION_Y + bottom <= cv.SAFE_BOTTOM


def test_slow_scenes_rise_out_of_black(s, tmp_path, monkeypatch):
    script = cv.parse_script(SCRIPT)
    script["scenes"] = [dict(script["scenes"][0], pace="slow"), dict(script["scenes"][1], pace="slow"),
                        dict(script["scenes"][1], pace="slow", hit="boom"), dict(script["scenes"][1], pace="fast")]
    dips = []

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (dips.append((a[1], a[7])), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    asyncio.run(cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=script))
    assert [d for _, d in sorted(dips)] == [False, True, False, False]  # never the hook, never on top of a hit's own look
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image, ImageStat
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (200, 200, 200)).save(still)
    cv.render_scene([still], None, 1.0, tmp_path / "dip.mp4", dip=True)
    subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / "dip.mp4"), "-frames:v", "1", str(tmp_path / "d0.png")],
                   check=True, capture_output=True)
    assert ImageStat.Stat(Image.open(tmp_path / "d0.png").convert("L")).mean[0] < 40  # opens dark


def test_the_mix_is_levelled_to_tiktok_loudness(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    import re
    import subprocess
    from PIL import Image
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (90, 90, 90)).save(still)
    quiet = tmp_path / "quiet.m4a"
    subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", "sine=f=220:d=3,volume=0.02", str(quiet)],
                   check=True, capture_output=True)
    cv.render_scene([still], quiet, 3.0, tmp_path / "q.mp4")
    cv.normalise(tmp_path / "q.mp4", tmp_path / "loud.mp4")

    def loudness(path):
        out = subprocess.run([cv.ffmpeg(), "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])
    assert loudness(tmp_path / "q.mp4") < -30 and abs(loudness(tmp_path / "loud.mp4") + 14) < 1.5
    measured = cv.measure_loudness(tmp_path / "q.mp4")  # measured first, so the levelling is one even gain
    assert measured and measured["input_i"] < -30


def test_the_spoken_word_pops_up_a_little():
    def height(im, colour):
        rows = [y for y in range(im.height) if any(im.getpixel((x, y))[:3] == colour and im.getpixel((x, y))[3]
                                                   for x in range(0, im.width, 3))]
        return rows[-1] - rows[0] if rows else 0
    accent = (232, 197, 71)
    lit = cv.caption_image(["hello", "there"], 0, accent)
    flat = cv.caption_image(["hello", "there"], 0, accent, ["hello"])  # a punch word is already its biggest
    assert height(lit, accent) > 0 and height(flat, accent) > height(lit, accent)
    assert cv.PUNCH_SCALE > cv.LIT_SCALE > 1


def test_scenes_render_two_at_a_time(monkeypatch):
    import threading
    import time as _time
    busy, peak, lock = [0], [0], threading.Lock()

    def slow_render(*job):
        with lock:
            busy[0] += 1
            peak[0] = max(peak[0], busy[0])
        _time.sleep(0.05)
        with lock:
            busy[0] -= 1
    monkeypatch.setattr(cv, "render_scene", slow_render)
    asyncio.run(cv.render_all([(i,) for i in range(6)]))
    assert peak[0] == cv.RENDER_JOBS

    def broken(*job):
        raise RuntimeError("ffmpeg failed")
    monkeypatch.setattr(cv, "render_scene", broken)
    with pytest.raises(RuntimeError, match="ffmpeg failed"):
        asyncio.run(cv.render_all([(1,), (2,)]))


def test_scene_voices_are_fetched_side_by_side_but_kept_in_order(s, tmp_path, monkeypatch):
    live, most, seconds = [0], [0], []

    async def no_picture(*a, **k):
        return None

    async def narrate(http, settings, text, voice, target, words=None, pace="normal", narrator=""):
        live[0] += 1
        most[0] = max(most[0], live[0])
        await asyncio.sleep(0.05 if text.startswith("The") else 0.01)  # the first scene's voice is the slowest
        live[0] -= 1
        target.write_bytes(text.encode())
        return True
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", narrate)
    monkeypatch.setattr(cv, "audio_seconds", lambda voice: 2.0 + len(voice.read_bytes()) / 100)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, secs, out, *a: (seconds.append((out.name, audio.name)),
                                                                                  out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    scenes = [{"narration": "The phone buzzed."}, {"narration": "Nobody answered."}, {"narration": "Run."}]
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "scenes": scenes}))
    asyncio.run(cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=script))
    assert 1 < most[0] <= cv.VOICE_JOBS
    assert sorted(seconds) == [("scene0.mp4", "scene0.mp3"), ("scene1.mp4", "scene1.mp3"), ("scene2.mp4", "scene2.mp3")]


def test_voices_and_pictures_are_fetched_at_the_same_time(s, tmp_path, monkeypatch):
    busy, overlap = {"voice": 0}, []

    async def picture(*a, **k):
        await asyncio.sleep(0.01)
        overlap.append(busy["voice"] > 0)  # a voice is still being fetched while this picture arrives
        return None

    async def narrate(*a, **k):
        busy["voice"] += 1
        await asyncio.sleep(0.05)
        busy["voice"] -= 1
        return False
    monkeypatch.setattr(cv, "fetch_picture", picture)
    monkeypatch.setattr(cv, "narrate", narrate)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    asyncio.run(cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=cv.parse_script(SCRIPT)))
    assert any(overlap)


def test_a_failed_picture_stops_the_voice_fetches(s, tmp_path, monkeypatch):
    finished = []

    async def broken(*a, **k):
        raise RuntimeError("picture service down")

    async def narrate(*a, **k):
        await asyncio.sleep(0.2)
        finished.append(1)
        return False
    monkeypatch.setattr(cv, "fetch_picture", broken)
    monkeypatch.setattr(cv, "narrate", narrate)

    async def go():
        with pytest.raises(RuntimeError):
            await cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=cv.parse_script(SCRIPT))
        await asyncio.sleep(0.3)
    asyncio.run(go())
    assert finished == []


def test_the_voice_gets_a_studio_polish(tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    from PIL import Image
    still, voice = tmp_path / "s.png", tmp_path / "v.m4a"
    Image.new("RGB", (cv.W, cv.H), (10, 10, 10)).save(still)
    cv.run(["-f", "lavfi", "-i", "sine=f=220:d=1", "-c:a", "aac", str(voice)])
    for kw in ({}, {"hit": "boom"}):  # with and without a sound effect, the polished voice still renders
        cv.render_scene([still], voice, 1.0, tmp_path / "s.mp4", **kw)
        assert cv.audio_seconds(tmp_path / "s.mp4") >= 0.99
    seen = []
    monkeypatch.setattr(cv, "run", lambda args: seen.append(" ".join(args)))
    cv.render_scene([still], voice, 1.0, tmp_path / "a.mp4")
    cv.render_scene([still], None, 1.0, tmp_path / "b.mp4")  # silence needs no polish
    assert cv.VOICE_POLISH in seen[0] and cv.VOICE_POLISH not in seen[1]


def test_lore_is_told_in_a_warm_storyteller_voice(s, tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    from PIL import Image
    still, voice = tmp_path / "s.png", tmp_path / "v.m4a"
    Image.new("RGB", (cv.W, cv.H), (10, 10, 10)).save(still)
    cv.run(["-f", "lavfi", "-i", "sine=f=140:d=1", "-c:a", "aac", str(voice)])
    cv.render_scene([still], voice, 1.0, tmp_path / "warm.mp4", tone="storyteller")  # ffmpeg takes the tone
    assert cv.audio_seconds(tmp_path / "warm.mp4") >= 0.99
    seen = []
    monkeypatch.setattr(cv, "run", lambda args: seen.append(" ".join(args)))
    cv.render_scene([still], voice, 1.0, tmp_path / "a.mp4", tone="storyteller")
    cv.render_scene([still], voice, 1.0, tmp_path / "b.mp4")
    cv.render_scene([still], None, 1.0, tmp_path / "c.mp4", tone="storyteller")  # silence gets nothing
    tone = cv.VOICE_TONES["storyteller"]
    assert tone in seen[0] and tone not in seen[1] and tone not in seen[2]
    assert cv.STYLE_VOICE_TONE["lore"] == "storyteller" and cs.account(cs.load(s), "lowkey.lore")["style"] == "lore"


def test_scene_sound_fades_at_the_cuts_so_joins_never_click(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    import array
    import subprocess
    from PIL import Image
    still, tone = tmp_path / "s.png", tmp_path / "tone.m4a"
    Image.new("RGB", (cv.W, cv.H), (90, 90, 90)).save(still)
    subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", "sine=f=440:d=3,volume=0.8", str(tone)],
                   check=True, capture_output=True)
    cv.render_scene([still], tone, 2.0, tmp_path / "s.mp4")  # the voice is still sounding at the cut
    raw = subprocess.run([cv.ffmpeg(), "-i", str(tmp_path / "s.mp4"), "-ac", "1", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    samples = array.array("h", raw)
    loudest = max(abs(v) for v in samples[len(samples) // 3: 2 * len(samples) // 3])
    assert loudest > 3000
    assert max(abs(v) for v in samples[-900:]) < loudest * 0.1  # faded right down at the cut, not chopped off
    assert max(abs(v) for v in samples[:100]) < loudest * 0.5  # and eased in at the start


def test_scenes_are_encoded_to_keep_dark_gradients_smooth(tmp_path, monkeypatch):
    from PIL import Image
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (10, 10, 10)).save(still)
    seen = []
    monkeypatch.setattr(cv, "run", seen.append)
    cv.render_scene([still], None, 1.0, tmp_path / "a.mp4")
    args = seen[0]
    assert args[args.index("-c:v") + 1] == "libx264" and "aq-mode=3" in args[args.index("-x264-params") + 1]


def test_in_between_audio_keeps_a_high_bitrate_and_only_the_finish_is_squeezed(tmp_path, monkeypatch):
    from PIL import Image
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (10, 10, 10)).save(still)
    seen = []
    monkeypatch.setattr(cv, "run", lambda args: seen.append(args[args.index("-b:a") + 1]))
    monkeypatch.setattr(cv, "audio_seconds", lambda path: 5.0)
    cv.render_scene([still], None, 1.0, tmp_path / "a.mp4")
    cv.add_ambience(tmp_path / "a.mp4", next(iter(cv.AMBIENCE)), tmp_path / "b.mp4")
    cv.add_music(tmp_path / "b.mp4", tmp_path / "track.mp3", tmp_path / "c.mp4")
    cv.normalise(tmp_path / "c.mp4", tmp_path / "d.mp4")
    assert seen == [cv.WORK_AUDIO] * 3 + [cv.FINAL_AUDIO]
    assert int(cv.WORK_AUDIO[:-1]) > int(cv.FINAL_AUDIO[:-1]) >= 160


def test_caption_pictures_for_every_scene_are_drawn_side_by_side(s, tmp_path, monkeypatch):
    import threading
    import time
    lock, live, most, given = threading.Lock(), [0], [0], []

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False

    def track(timed, seconds, accent, work, name, punch=()):
        with lock:
            live[0] += 1
            most[0] = max(most[0], live[0])
        time.sleep(0.1)
        with lock:
            live[0] -= 1
        return work / f"{name}.txt"
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "caption_track", track)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, captions=None, *a: (
        given.append((out.name, captions.name)), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    account = {**cs.load(s)["accounts"][0], "captions": True}
    asyncio.run(cv.make(None, None, s, account, tmp_path, script=cv.parse_script(SCRIPT)))
    assert most[0] > 1
    assert sorted(given) == [("scene0.mp4", "cap0.txt"), ("scene1.mp4", "cap1.txt")]


def test_silence_after_the_last_word_is_trimmed(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    voice, hush = tmp_path / "v.mp3", tmp_path / "h.mp3"
    cv.run(["-f", "lavfi", "-i", "sine=f=300:d=1", "-af", "apad=pad_dur=1.2", str(voice)])  # 1s of speech, 1.2s of air
    cv.trim_tail(voice)
    assert 0.95 < cv.audio_seconds(voice) < 1.4
    cv.run(["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "1", str(hush)])
    cv.trim_tail(hush)  # nothing but silence: left as it was rather than emptied
    assert cv.audio_seconds(hush) >= 0.95
    assert not list(tmp_path.glob("*-trim*"))


def test_silence_before_the_first_word_is_trimmed_and_the_words_move_with_it(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    voice = tmp_path / "v.mp3"
    cv.run(["-f", "lavfi", "-i", "sine=f=300:d=1", "-af", "adelay=700:all=1", str(voice)])  # 0.7s of air first
    lead = cv.trim_head(voice)
    assert 0.55 < lead < 0.75 and cv.audio_seconds(voice) < 1.3
    words = [(0.72, 1.1, "Run"), (1.2, 1.6, "now"), (0.1, 0.3, "uh")]
    cv.shift_words(words, lead)
    assert words[0][0] < 0.2 and words[1][1] == pytest.approx(1.6 - lead) and words[2][:2] == (0.0, 0.0)
    assert not list(tmp_path.glob("*-head*"))


def test_caption_timings_follow_the_trimmed_voice(s, tmp_path, monkeypatch):
    timings = []

    async def no_picture(*a, **k):
        return None

    async def narrate(http, settings, text, voice, target, words=None, pace="normal", narrator=""):
        target.write_bytes(b"voice")
        words.append((0.6, 0.9, "Hello"))
        return True
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", narrate)
    monkeypatch.setattr(cv, "trim_head", lambda voice: 0.5)
    monkeypatch.setattr(cv, "trim_tail", lambda voice: None)
    monkeypatch.setattr(cv, "audio_seconds", lambda voice: 2.0)
    monkeypatch.setattr(cv, "caption_track", lambda timed, *a, **k: timings.append(timed))
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    account = {**cs.load(s)["accounts"][0], "captions": True}
    asyncio.run(cv.make(None, None, s, account, tmp_path, script=cv.parse_script(SCRIPT)))
    assert timings and all(t == [(pytest.approx(0.1), pytest.approx(0.4), "Hello")] for t in timings)


def test_spare_time_and_pauses_follow_each_scenes_pace():
    fast, normal, slow = cv.fit_to_length([4.0, 4.0, 4.0], paces=["fast", "normal", "slow"])
    assert fast < normal < slow and fast + normal + slow == pytest.approx(cv.MIN_LENGTH, abs=0.05)
    assert cv.fit_to_length([4.0] * 3) == cv.fit_to_length([4.0] * 3, paces=["normal"] * 3)  # unchanged without paces
    long = cv.fit_to_length([20.0, 20.0, 20.0], paces=["fast", "normal", "slow"])  # no spare time: only the breath
    assert long[0] == pytest.approx(20.2, abs=0.05) and long[2] == pytest.approx(20.6, abs=0.05)
    assert cv.fit_to_length([4.0, 4.0], paces=["weird", "normal"])[0] > 4.0  # an unknown pace counts as normal


def test_a_dropped_voice_is_asked_for_once_more(s, tmp_path, monkeypatch):
    calls = {}

    async def no_picture(*a, **k):
        return None

    async def flaky(http, settings, text, voice, target, words=None, pace="normal", narrator=""):
        calls[text] = calls.get(text, 0) + 1
        words.append((0.0, 0.2, "half"))  # a failed try's half-timings must not leak into the retry
        if text.startswith("The") and calls[text] == 1:
            return False
        target.write_bytes(b"voice")
        return True
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", flaky)
    monkeypatch.setattr(cv, "trim_head", lambda voice: 0.0)
    monkeypatch.setattr(cv, "trim_tail", lambda voice: None)
    monkeypatch.setattr(cv, "audio_seconds", lambda voice: 2.0)
    audio = []
    monkeypatch.setattr(cv, "render_scene", lambda stills, a, seconds, out, *r: (audio.append(a), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    scenes = [{"narration": "The phone buzzed."}, {"narration": "Nobody answered."}]
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "scenes": scenes}))
    asyncio.run(cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=script))
    assert calls == {"The phone buzzed.": 2, "Nobody answered.": 1}
    assert all(a is not None for a in audio)  # both scenes ended up voiced


def test_scenes_left_without_a_voice_are_named_in_the_checks(s, tmp_path, monkeypatch):
    async def no_picture(*a, **k):
        return None

    async def half(http, settings, text, voice, target, words=None, pace="normal", narrator=""):
        if text.startswith("The"):
            return False
        target.write_bytes(b"voice")
        return True
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", half)
    monkeypatch.setattr(cv, "trim_head", lambda voice: 0.0)
    monkeypatch.setattr(cv, "trim_tail", lambda voice: None)
    monkeypatch.setattr(cv, "audio_seconds", lambda voice: 2.0)
    monkeypatch.setattr(cv, "check_video", lambda video: [])
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    scenes = [{"narration": "Nobody answered."}, {"narration": "The phone buzzed."}, {"narration": "Nothing moved."}]
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "scenes": scenes}))
    out = asyncio.run(cv.make(None, None, s, cs.load(s)["accounts"][0], tmp_path, script=script))
    assert out["checks"] == ["no voice on scene 2 (the voice service failed; remake it)"]


def test_a_full_song_skips_its_quiet_intro(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(cv, "run", lambda args: seen.append(args))
    lengths = {"video.mp4": 61.0, "song.mp3": 180.0, "jingle.mp3": 20.0}
    monkeypatch.setattr(cv, "audio_seconds", lambda path: lengths[Path(path).name])
    cv.add_music(tmp_path / "video.mp4", tmp_path / "song.mp3", tmp_path / "a.mp4")
    cv.add_music(tmp_path / "video.mp4", tmp_path / "jingle.mp3", tmp_path / "b.mp4")
    song, jingle = seen
    assert song[song.index("-ss") + 1] == f"{cv.MUSIC_SKIP:.2f}" and "afade=t=in" in " ".join(song)
    assert jingle[jingle.index("-ss") + 1] == "0.00" and "afade=t=in" not in " ".join(jingle)


def test_captions_cast_a_soft_shadow_below_the_words():
    im = cv.caption_image(["run"], 0, (232, 197, 71))
    alpha = im.getchannel("A")
    left, top, right, bottom = alpha.point(lambda a: 255 if a > 200 else 0).getbbox()  # the solid word
    below = [im.getpixel((x, bottom + 4)) for x in range(left, right)]
    assert any(p[3] > 0 and p[:3] == (0, 0, 0) for p in below)  # dark, see-through shade under the word
    assert all(p[3] < 255 for p in below)


def test_full_screen_looks_ask_for_tall_pictures(s, tmp_path, monkeypatch):
    sizes = []

    async def picture(http, description, style, seed, size=(1024, 1024)):
        sizes.append(size)
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    for style, want in (("cinematic", cv.TALL_PICTURE), ("drama", cv.TALL_PICTURE), ("noir", (1024, 1024))):
        sizes.clear()
        account = {**cs.load(s)["accounts"][0], "style": style}
        asyncio.run(cv.make(None, None, s, account, tmp_path, script=cv.parse_script(SCRIPT)))
        assert sizes and set(sizes) == {want}
    w, h = cv.TALL_PICTURE
    assert abs(w / h - cv.W / cv.H) < 0.01 and w * h <= 1024 * 1024 * 1.3


def test_a_fresh_caption_line_pops_in_smaller_for_two_frames(tmp_path):
    words = [(0.0, 0.6, "Run"), (0.6, 1.2, "now"), (1.2, 1.3, "Go")]
    text = cv.caption_track(words, 2.0, (232, 197, 71), tmp_path, "cap").read_text()
    lines = text.splitlines()
    first = lines.index("file 'cap-0-pop.png'")
    assert lines[first + 1] == f"duration {cv.POP_SECONDS:.3f}" and lines[first + 2] == "file 'cap-0.png'"
    full = cv.caption_image(["Run", "now"], 0, (232, 197, 71))
    small = cv.popped(full)
    assert small.size == full.size
    assert small.getchannel("A").getbbox()[2] - small.getchannel("A").getbbox()[0] < \
        full.getchannel("A").getbbox()[2] - full.getchannel("A").getbbox()[0]


def test_every_page_but_lowkey_lore_is_switched_off_until_the_user_sets_it_up(s, monkeypatch):
    monkeypatch.setattr(cs, "SWITCH_OFF_OTHERS", True)
    data = cs.load(s)
    assert [a["name"] for a in data["accounts"] if not a["off"]] == ["lowkey.lore"]
    cs.save(s, data)
    assert [j[0] for j in creator.todays_jobs(s, cs.load(s), date.today())] == ["lowkey.lore"] * 3
    with pytest.raises(ValueError, match="switched off"):
        asyncio.run(creator.make_one(s, "karma.receipts"))
    assert "switched off" in creator.update_account(s, {"account": "karma.receipts", "off": True})
    creator.update_account(s, {"account": "karma.receipts", "off": False})  # the user switches a page back on
    assert {j[0] for j in creator.todays_jobs(s, cs.load(s), date.today())} == {"lowkey.lore", "karma.receipts"}
    assert not cs.find_account(cs.load(s), "karma.receipts")["off"]  # and it stays on: the switch-off runs once


def test_lore_gets_the_full_screen_detailed_look_once(s, monkeypatch):
    monkeypatch.setattr(cs, "SWITCH_OFF_OTHERS", True)
    path = Path(s.memory_dir)
    data = cs.load(s)
    data["accounts"][0]["style"] = "noir"  # how every existing studio has it
    data.pop("lore_look")
    cs.save(s, data)
    lore = cs.load(s)["accounts"][0]
    assert lore["name"] == "lowkey.lore" and lore["style"] == "lore"
    assert cv.picture_size(lore) == (cv.W, cv.H)  # full phone resolution, so detail survives the zoom
    assert "hyper-detailed" in cv.LOOKS["lore"] and cv.FRAMES["lore"] is cv.cinematic_frame
    fresh = cs.load(s)
    fresh["accounts"][0]["style"] = "noir"  # the user picks the old card again later: it stays their choice
    cs.save(s, fresh)
    assert cs.load(s)["accounts"][0]["style"] == "noir"
    assert path.exists()


def test_lore_scenes_get_a_third_shot_and_the_storyteller_voice(s, tmp_path, monkeypatch):
    from PIL import Image
    asked, voices, rendered = [], [], []

    async def picture(http, description, style, seed, size=(1024, 1024)):
        asked.append((description, size))
        return Image.new("RGB", (64, 64))

    async def narrate(http, settings, text, voice, target, words=None, pace="normal", narrator=""):
        voices.append(voice or narrator)
        return False
    monkeypatch.setattr(cv, "fetch_picture", picture)
    monkeypatch.setattr(cv, "narrate", narrate)
    monkeypatch.setattr(cv, "VOICE_TRIES", 1)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (rendered.append(list(stills)),
                                                                                     out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    scenes = [{"narration": "She pressed play.", "picture": "a phone", "closeup": "her thumb", "detail": "rain on glass"},
              {"narration": "It said her name.", "picture": "a kitchen", "closeup": "a mug"}]
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "scenes": scenes}))
    lore = cs.load(s)["accounts"][0]
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert [len(r) for r in rendered] == [3, 2]  # the picture changes every couple of seconds
    assert {size for _, size in asked} == {(cv.W, cv.H)} and len(asked) == 5
    assert voices == ["en-US-AndrewMultilingualNeural"] * 2
    rendered.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "style": "cinematic"}, tmp_path, script=script))
    assert [len(r) for r in rendered] == [2, 2]  # other looks keep two shots


def test_an_unknown_narrator_falls_back_to_the_default_voice(s, tmp_path, monkeypatch):
    import edge_tts
    tried = []

    class Talk:
        def __init__(self, text, voice, **k):
            tried.append(voice)
            self.voice = voice

        async def stream(self):
            if self.voice != cv.DEFAULT_VOICE:
                raise ValueError("No such voice")
            yield {"type": "audio", "data": b"mp3"}
    monkeypatch.setattr(edge_tts, "Communicate", Talk)
    assert asyncio.run(cv.narrate(None, s, "Hello.", "", tmp_path / "v.mp3", [], narrator="en-XX-NobodyNeural"))
    assert tried == ["en-XX-NobodyNeural", cv.DEFAULT_VOICE]


def test_a_three_shot_scene_lasts_exactly_as_long(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    from PIL import Image
    stills = []
    for i, colour in enumerate(((200, 40, 40), (40, 200, 40), (40, 40, 200))):
        Image.new("RGB", (cv.W, cv.H), colour).save(tmp_path / f"{i}.png")
        stills.append(tmp_path / f"{i}.png")
    cv.render_scene(stills, None, 3.0, tmp_path / "three.mp4")
    assert abs(cv.audio_seconds(tmp_path / "three.mp4") - 3.0) < 0.1


def test_lore_scenes_have_living_film_texture_so_a_still_never_looks_frozen(tmp_path, monkeypatch):
    pytest.importorskip("imageio_ffmpeg")
    from PIL import Image
    monkeypatch.setattr(cv, "MIN_LENGTH", 1.0)
    Image.new("RGB", (cv.W, cv.H), (90, 110, 140)).save(tmp_path / "still.png")
    for name, atmosphere in (("plain", ""), ("film", "film")):
        cv.render_scene([tmp_path / "still.png"], None, 4.0, tmp_path / f"{name}.mp4", atmosphere=atmosphere)
    assert any("frozen still" in p for p in cv.check_video(tmp_path / "plain.mp4"))  # a flat still sits dead
    assert not any("frozen still" in p for p in cv.check_video(tmp_path / "film.mp4"))  # the grain keeps it alive
    assert cv.STYLE_ATMOSPHERE["lore"] == "film"


def test_lore_opens_on_a_flash_of_a_later_moment(s, tmp_path, monkeypatch):
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "teaser": "3"}))
    assert script["teaser"] == 3 and cv.parse_script(SCRIPT)["teaser"] == 0
    script["scenes"] = [dict(script["scenes"][i % 2]) for i in range(4)]
    teasers = {}

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        teasers.__setitem__(a[1], (a[9], [Path(x).name for x in stills])), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert Path(teasers[0][0]).name == "scene2.png" and all(teasers[i][0] is None for i in (1, 2, 3))
    teasers.clear()  # another look gets no flash
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert teasers[0][0] is None
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image
    flash, main = tmp_path / "flash.png", tmp_path / "main.png"
    Image.new("RGB", (cv.W, cv.H), (220, 30, 30)).save(flash)
    Image.new("RGB", (cv.W, cv.H), (30, 30, 220)).save(main)
    cv.render_scene([main], None, 2.0, tmp_path / "t.mp4", teaser=flash)

    def colour(n):
        out = tmp_path / f"f{n}.png"
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / "t.mp4"), "-vf", f"select=eq(n\\,{n})", "-frames:v", "1",
                        str(out)], check=True, capture_output=True)
        return Image.open(out).convert("RGB").getpixel((cv.W // 2, cv.H // 2))
    first, after = colour(1), colour(round(cv.TEASER_SECONDS * cv.FPS) + 3)
    assert first[0] > first[2] and after[2] > after[0]  # the flash, then the scene's own shot
    assert abs(cv.audio_seconds(tmp_path / "t.mp4") - 2.0) < 0.15  # inside the scene's length, not added on


def test_a_tension_riser_builds_into_a_lore_reveal(s, tmp_path, monkeypatch):
    script = cv.parse_script(SCRIPT)
    base = script["scenes"][0]
    script["scenes"] = [dict(base), dict(base, hit="boom"), dict(base), dict(base, hit="glitch"), dict(base),
                        dict(base, hit="sting"), dict(base), dict(base, hit="boom")]  # the 4th hit is over MAX_HITS
    risers = {}

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        risers.__setitem__(a[1], (a[4], a[11])), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert [risers[i][1] for i in range(8)] == [True, False, False, False, True, False, False, False]
    assert [risers[i][0] for i in range(8)] == ["", "boom", "", "glitch", "", "sting", "", ""]
    risers.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "sfx": False}, tmp_path, script=script))
    assert not any(r for _, r in risers.values())  # sound effects off: no riser either
    risers.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert not any(r for _, r in risers.values())
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (10, 10, 10)).save(still)
    cv.render_scene([still], None, 4.0, tmp_path / "r.mp4", riser=True)
    cv.render_scene([still], None, 4.0, tmp_path / "q.mp4", riser=True, whoosh=True)

    def loudness(video, start, length):
        got = subprocess.run([cv.ffmpeg(), "-ss", str(start), "-t", str(length), "-i", str(video), "-af", "volumedetect",
                              "-f", "null", "-"], capture_output=True, text=True).stderr
        return float(got.split("mean_volume:")[1].split("dB")[0])
    for video in ("r.mp4", "q.mp4"):
        assert abs(cv.audio_seconds(tmp_path / video) - 4.0) < 0.15
        assert loudness(tmp_path / video, 3.3, 0.5) > loudness(tmp_path / video, 2.0, 0.5) + 6  # it swells to the cut
    assert loudness(tmp_path / "r.mp4", 0.2, 1.0) < -60  # silent before the swell starts


def test_lore_gets_its_own_dark_score_when_no_track_is_dropped_in(s, tmp_path, monkeypatch):
    assert cv.score_notes("tense slow piano") == cv.SCORE_NOTES["tense"] and cv.score_notes("") == cv.SCORE_NOTES["calm"]
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "mood": "eerie ambient"}))
    scored = []

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    monkeypatch.setattr(cv, "audio_seconds", lambda path: 70.0)
    monkeypatch.setattr(cv, "normalise", lambda a, b: b.write_bytes(a.read_bytes()))
    monkeypatch.setattr(cv, "make_score", lambda seconds, mood, out: (scored.append((seconds, mood)), out.write_bytes(b"w")))
    monkeypatch.setattr(cv, "add_music", lambda video, track, out, drops=(): (scored.append(track.name), out.write_bytes(b"mp4")))
    lore = cs.account(cs.load(s), "lowkey.lore")
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert scored == [(70.0, "eerie ambient"), "score.wav"]
    scored.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    asyncio.run(cv.make(None, None, s, {**lore, "music": False}, tmp_path, script=script))
    assert scored == []  # other looks, or music switched off, stay as they were
    mine = tmp_path / "mine.mp3"
    monkeypatch.setattr(cv, "music_for", lambda *a: mine)
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert scored == ["mine.mp3"]  # a track the user dropped in always wins
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    cv.make_score(5.0, "tense", tmp_path / "score.wav")
    assert cv.audio_seconds(tmp_path / "score.wav") > 5.0 + cv.MUSIC_SKIP  # never runs out and loops


def test_blank_or_wrong_shape_pictures_are_asked_for_again():
    import io
    import random as rnd
    from PIL import Image

    def png(im):
        out = io.BytesIO()
        im.save(out, "PNG")
        return out.getvalue()
    rnd.seed(1)
    real = Image.new("RGB", (108, 192))
    real.putdata([(rnd.randrange(256),) * 3 for _ in range(108 * 192)])
    blank = Image.new("RGB", (108, 192), (12, 12, 12))
    notice = real.resize((150, 150))  # a square "busy" card where a tall shot was asked for
    assert cv.usable_picture(real, (1080, 1920)) and not cv.usable_picture(blank, (1080, 1920))
    assert not cv.usable_picture(notice, (1080, 1920)) and cv.usable_picture(notice, (1024, 1024))
    for first, retried in ((blank, True), (notice, True), (real, False)):
        sent = [first, real]

        def handler(request):
            return httpx.Response(200, content=png(sent.pop(0)), headers={"content-type": "image/png"})
        got = asyncio.run(cv.fetch_picture(httpx.AsyncClient(transport=httpx.MockTransport(handler)), "a door", "lore", 1,
                                           size=(1080, 1920)))
        assert got.size == real.size and (len(sent) == 0) == retried
    def always_blank(request):
        return httpx.Response(200, content=png(blank), headers={"content-type": "image/png"})
    assert asyncio.run(cv.fetch_picture(httpx.AsyncClient(transport=httpx.MockTransport(always_blank)), "a door",
                                        "lore", 1, size=(1080, 1920))) is None  # then the scene's own fallbacks take over


def test_broken_script_json_is_repaired_not_fatal():
    import tiktokstudio_video as cv

    raw = ('Here you go:\n{"title": "The lighthouse", "scenes": [{"narration": "She whispered "stay" and left."}, '
           '{"narration": "Nobody\nanswered."}, {"narration": "The light came on anyway."}],')
    script = cv.parse_script(raw)
    assert script["title"] == "The lighthouse" and len(script["scenes"]) == 3
    assert '"stay"' in script["scenes"][0]["narration"]


async def test_an_unreadable_script_gets_a_fixed_copy_before_failing():
    from types import SimpleNamespace

    import tiktokstudio_video as cv
    from config import Settings

    good = '{"title": "T", "scenes": [{"narration": "One."}, {"narration": "Two."}]}'
    replies = ["no json here at all", good]
    sent = []

    async def create(**kwargs):
        sent.append(kwargs["messages"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=replies.pop(0))])

    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    script = await cv._script_reply(client, Settings(), "write it")
    assert script["title"] == "T" and "doesn't parse" in sent[1][-1]["content"]


async def test_a_script_that_never_parses_is_saved_and_explained_plainly(tmp_path):
    from dataclasses import replace
    from types import SimpleNamespace

    import pytest

    import tiktokstudio_video as cv
    from config import Settings

    async def create(**kwargs):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="sorry, no script today")])

    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    with pytest.raises(ValueError, match="couldn't read it back"):
        await cv._script_reply(client, replace(Settings(), memory_dir=str(tmp_path)), "write it")
    saved = list((tmp_path / "TikTok" / "broken-scripts").glob("*.txt"))
    assert saved and "no script today" in saved[0].read_text(encoding="utf-8")


def test_clipzz_cuts_one_moment_and_the_next_minute_follows_at_200k_unlabelled(s, monkeypatch):
    s = replace(s, twitch_client_id="id", twitch_client_secret="sec")
    allow(s, "Clipzz", "kai")
    data = cs.load(s)
    a = cs.account(data, "Clipzz")
    assert (a["min_views"], a["stream_min_views"], a["continue_at"]) == (0, 200_000, 200_000)
    a["off"] = False
    cs.save(s, data)

    stream = "https://www.twitch.tv/videos/9"
    moment = {**clip(1, "kai", 25, 300_000), "vod": (stream, 600.0, 3600.0), "stream_views": 900_000}
    small = {**clip(3, "kai", 25, 900_000), "vod": ("https://www.twitch.tv/videos/8", 50.0, 3600.0), "stream_views": 1000}

    async def fake_top(http, settings, era, streamers, category):
        return [small, clip(2, "kai", 20, 50_000), moment]  # small's stream had too few views; clip 2 has no stream
    monkeypatch.setattr(twitch, "top_clips", fake_top)
    cuts = []

    def fake_download(url, target, section=None):
        cuts.append((url, section))
        return (target.with_suffix(".mp4").write_bytes(b"c"), target.with_suffix(".mp4"))[1]
    monkeypatch.setattr(clips, "download", fake_download)
    monkeypatch.setattr(clips, "portrait", lambda source, layer, out: out.write_bytes(b"p"))
    monkeypatch.setattr(clips, "level", lambda part: None)
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    monkeypatch.setattr(cv, "video_facts", lambda path: "1:02")

    async def hook_reply(**kwargs):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text='"Part 2: he really said it (2)"')])
    creator._ctx.update(client=SimpleNamespace(messages=SimpleNamespace(create=hook_reply)))

    asyncio.run(creator.make_in_background(s, [("Clipzz", "", None)]))
    first = cs.load(s)["videos"][-1]
    assert first["status"] == "ready" and cuts == [(stream, (597.0, 659.0))]  # 3s lead-in, a minute of the stream
    assert first["moment"]["end"] == 659.0 and "stream watched 900,000 times" in first["notes"]

    data = cs.load(s)
    data["videos"][-1].update(status="posted", views=150_000)
    cs.save(s, data)
    assert creator.continuations_due(cs.load(s)) == []  # under 200k: nothing yet
    data["videos"][-1]["views"] = 250_000
    cs.save(s, data)
    due = creator.continuations_due(cs.load(s))
    assert [v["id"] for v in due] == [first["id"]]

    asyncio.run(creator.make_in_background(s, [("Clipzz", "", due[0])]))
    nxt = cs.load(s)["videos"][-1]
    assert cuts[-1] == (stream, (659.0, 721.0))  # the very next minute of the stream
    assert nxt["status"] == "ready" and nxt["continues"] == first["id"] and nxt.get("part", 1) == 1
    for text in (nxt["title"], nxt["caption"], nxt["hook"]):
        assert "part" not in text.lower() and "(2)" not in text
    assert creator.continuations_due(cs.load(s)) == []  # one follow-on per video; it must earn 200k itself


def test_a_moment_never_runs_past_the_end_of_its_stream():
    assert clips.moment_window(100.0, 3600.0) == (100.0, 162.0)
    assert clips.moment_window(3560.0, 3600.0) is None  # under a minute left
    assert clips.standalone("Part 3: the rematch (2)") == "the rematch"


def test_a_moment_many_viewers_clipped_beats_one_big_clip():
    stream, other = ("https://twitch.tv/videos/1", 10.0, 0.0), ("https://twitch.tv/videos/2", 10.0, 0.0)
    found = asyncio.run(clips.find_moments([
        {**clip(1, views=50_000), "vod": (stream[0], 1000.0, 0.0)},
        {**clip(2, views=40_000), "vod": (stream[0], 1020.0, 0.0)},  # same moment, another viewer
        {**clip(3, views=30_000), "vod": (stream[0], 1045.0, 0.0)},
        {**clip(4, views=100_000), "vod": (other[0], 500.0, 0.0)},  # one big clip alone
        {**clip(5, views=10_000), "vod": (stream[0], 3000.0, 0.0)},  # a separate moment, same stream
    ], {}))
    top = found[0]
    assert top["moment_clips"] == 3 and top["vod"][1] == 1000.0 and top["id"] == "c1"
    assert [m["moment_clips"] for m in found] == [3, 1, 1] and len(found) == 3


def test_a_rejected_moment_only_rules_out_that_stretch_of_the_stream():
    used = {clips.moment_key("https://twitch.tv/videos/1", 997.0)}
    assert clips.overlaps("https://twitch.tv/videos/1", 1050.0, used)
    assert not clips.overlaps("https://twitch.tv/videos/1", 3000.0, used)  # the rest of the stream is fine
    assert not clips.overlaps("https://twitch.tv/videos/2", 997.0, used)


def test_review_fixes_for_moment_videos(s):
    stream = "https://twitch.tv/videos/1"
    # a fresh moment can't share footage with a used stretch, and a follow-on can't re-cut one
    used = [clips.moment_key(stream, 100.0, 162.0), clips.moment_key(stream, 221.0, 283.0)]
    assert clips.overlaps(stream, 150.0, used) and not clips.overlaps(stream, 162.0, used, 221.0)
    assert clips.overlaps(stream, 224.0, used, 286.0)
    prev = {"id": "v1", "hook": "He snapped", "moment": {"vod": stream, "end": 162.0, "length": 0,
                                                         "clip": {"broadcaster_name": "kai"}}}
    with pytest.raises(ValueError, match="already in another video"):
        asyncio.run(clips.make_continuation(s, {"used_clips": [clips.moment_key(stream, 200.0, 262.0)]},
                                            Path(s.memory_dir), prev))
    # without Claude a follow-on never repeats the earlier title
    assert asyncio.run(clips.continuation_hook(None, s, prev)) == "kai didn't stop there"
    # Twitch stream lengths are read, so a cut stops at the end of the stream
    assert twitch.seconds("3h8m33s") == 11313.0 and twitch.seconds("") == 0.0


def test_set_views_on_a_moment_video_talks_about_the_next_minute_not_parts(s):
    data = cs.load(s)
    data["videos"].append({"id": "v1", "account": "Clipzz", "title": "kai snapped", "status": "posted", "views": 0,
                           "moment": {"vod": "x", "end": 60.0, "length": 0, "clip": {}}})
    cs.save(s, data)
    said = creator.set_views(s, "v1", "150k")
    assert "200,000" in said and "part" not in said.lower()
    assert "next minute" in creator.set_views(s, "v1", "210k")

def test_the_opening_scenes_hold_the_least_so_the_video_starts_fast():
    held = cv.fit_to_length([4.0] * 10)
    assert held[0] == pytest.approx(4.35, abs=1 / cv.FPS)  # the hook keeps its own length: no padding at all
    assert held[1] < held[2] < held[3] and held[3] == pytest.approx(held[8], abs=0.1)  # then it eases off
    assert sum(held) == pytest.approx(cv.MIN_LENGTH)
    slow = cv.fit_to_length([4.0] * 10, paces=["slow"] * 10)  # pace still decides the rest
    assert slow[0] == pytest.approx(4.6, abs=1 / cv.FPS) and slow[3] > slow[1] > slow[0]
    few = cv.fit_to_length([4.0] * 4)  # too few scenes to hold the opening back: it would stretch the rest absurdly
    assert max(few) - min(few) < 0.1 and sum(few) == pytest.approx(cv.MIN_LENGTH)
    assert cv.fit_to_length([20.0] * 5)[0] == pytest.approx(20.35, abs=1 / cv.FPS)  # no spare time: nothing changes


def test_the_music_drops_out_just_before_a_lore_reveal(s, tmp_path, monkeypatch):
    assert cv.drop_times([3.0, 4.0, 5.0], ["", "", "boom"]) == [7.0]
    assert cv.drop_times([3.0, 4.0], ["boom", "sting"]) == []  # the first scene has nothing before it to cut
    assert cv.drop_gain([]) == "1" and cv.drop_gain([0.2]) == "1"  # too early for a gap: left alone
    gain = cv.drop_gain([7.0])
    level = lambda t: eval(gain.replace("clip", "c"), {"c": lambda x, lo, hi: min(hi, max(lo, x)), "t": t})
    assert level(5.0) == 1 and level(6.9) == pytest.approx(cv.DROP_LEVEL) and level(7.1) == 1
    script = json.loads(SCRIPT)
    script["scenes"][1]["hit"] = "boom"
    script = cv.parse_script(json.dumps(script))
    seen = []

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    monkeypatch.setattr(cv, "audio_seconds", lambda path: 30.0)
    monkeypatch.setattr(cv, "normalise", lambda a, b: b.write_bytes(a.read_bytes()))
    monkeypatch.setattr(cv, "music_for", lambda *a: tmp_path / "song.mp3")
    monkeypatch.setattr(cv, "add_music", lambda video, track, out, drops=(): (seen.append(list(drops)), out.write_bytes(b"m")))
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert seen == [[30.0], []]  # timed from the rendered scenes; other looks keep a steady bed
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import re
    import subprocess
    exe = cv.ffmpeg()
    subprocess.run([exe, "-y", "-v", "error", "-f", "lavfi", "-i", "color=black:s=64x64:d=4", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=stereo", "-t", "4", "-shortest", str(tmp_path / "v.mp4")], check=True)
    subprocess.run([exe, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=220:d=6", str(tmp_path / "t.wav")], check=True)
    cv.add_music(tmp_path / "v.mp4", tmp_path / "t.wav", tmp_path / "o.mp4", [2.5])

    def loud(start):
        out = subprocess.run([exe, "-v", "info", "-ss", str(start), "-t", "0.3", "-i", str(tmp_path / "o.mp4"),
                              "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
        return float(re.search(r"mean_volume: (-?[\d.]+|-inf)", out).group(1))
    assert loud(2.1) < loud(1.0) - 20 and loud(2.8) > loud(2.1) + 20


def test_the_planted_clue_flashes_back_as_the_twist_lands(s, tmp_path, monkeypatch):
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "clue": "2"}))
    assert script["clue"] == 2 and cv.parse_script(SCRIPT)["clue"] == 0
    assert "clue" in cv.SCRIPT_PROMPT
    shots = [["a0", "b0"], ["a1", "b1"], ["a2"], ["a3"], ["a4"]]
    assert cv.clue_flashback(shots, 2, ["", "", "sting", "boom", "boom"]) == {3: "b1"}  # its closeup, first boom after
    assert cv.clue_flashback(shots, 3, ["boom", "", "", "", "boom"]) == {4: "a2"}  # no closeup: the main shot
    assert cv.clue_flashback(shots, 4, ["boom", "", "", "", ""]) == {}  # no reveal after the clue
    assert cv.clue_flashback(shots, 0, ["", "boom"]) == {} and cv.clue_flashback(shots, 9, ["", "boom"]) == {}
    script["scenes"] = [dict(script["scenes"][i % 2]) for i in range(4)]
    script["scenes"][3]["hit"] = "boom"
    seen = {}

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        seen.__setitem__(a[1], (a[9], [Path(x).name for x in stills])), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    clue_shots = seen[1][1]
    assert Path(seen[3][0]).name == clue_shots[min(1, len(clue_shots) - 1)]
    assert all(seen[i][0] is None for i in (0, 1, 2))
    seen.clear()  # another look gets no flashback
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert seen[3][0] is None


def test_the_narrator_holds_a_beat_of_silence_before_a_lore_reveal(s, tmp_path, monkeypatch):
    lengths = cv.twist_beats([3.0, 4.0, 5.0], [2.9, 3.0, 4.5], ["", "boom", "boom"])
    assert lengths[0] == pytest.approx(2.9 + cv.TWIST_BEAT, abs=1 / cv.FPS)  # stretched for the pause
    assert lengths[1] == 4.0 and lengths[2] == 5.0  # already room enough, and the last scene leads into nothing
    assert cv.TWIST_BEAT >= cv.DROP_SECONDS  # the whole music drop falls in the narrator's silence
    assert cv.twist_beats([3.0, 4.0], [2.9, 3.0], ["", "sting"]) == [3.0, 4.0]
    script = json.loads(SCRIPT)
    script["scenes"][1]["hit"] = "boom"
    script = cv.parse_script(json.dumps(script))
    seen = {}

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "fit_to_length", lambda voiced, *a, **k: [v + 0.2 for v in voiced])
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        seen.__setitem__(a[1], seconds), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    beat = seen[0]
    seen.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert beat == pytest.approx(seen[0] - 0.2 + cv.TWIST_BEAT, abs=1 / cv.FPS)  # other looks keep their timing


def test_the_last_lore_line_is_said_close_and_dry(s, tmp_path, monkeypatch):
    assert "aecho" in cv.VOICE_TONES["storyteller"] and "aecho" not in cv.VOICE_TONES["close"]
    script = cv.parse_script(SCRIPT)
    script["scenes"] = [dict(script["scenes"][i % 2]) for i in range(4)]
    tones = {}

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        tones.__setitem__(a[1], a[10]), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert tones == {0: "storyteller", 1: "storyteller", 2: "storyteller", 3: "close"}
    tones.clear()  # other looks keep the plain voice to the end
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert set(tones.values()) == {""}
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image
    still, voice = tmp_path / "s.png", tmp_path / "v.m4a"
    Image.new("RGB", (cv.W, cv.H), (10, 10, 10)).save(still)
    subprocess.run([cv.ffmpeg(), "-y", "-f", "lavfi", "-i", "sine=f=300:d=1", str(voice)], check=True, capture_output=True)
    cv.render_scene([still], voice, 1.0, tmp_path / "close.mp4", tone="close")  # ffmpeg takes the tone
    assert cv.audio_seconds(tmp_path / "close.mp4") > 0.9


def test_rain_or_dust_drifts_over_lore_pictures(s, tmp_path, monkeypatch):
    from PIL import Image
    for kind in ("rain", "dust"):
        tile = Image.open(cv.particle_tile(kind, tmp_path / f"{kind}.png", seed=3))
        assert tile.size == (cv.W, 2 * cv.H) and tile.getchannel("A").getextrema()[1] > 0
        assert tile.crop((0, 0, cv.W, cv.H)).tobytes() == tile.crop((0, cv.H, cv.W, 2 * cv.H)).tobytes()  # loops
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "ambience": "rain"}))
    seen = []

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        seen.append(a[12]), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "add_ambience", lambda video, kind, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "make_score", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert len(seen) == 2 and all(p and p[1] == cv.PARTICLES["rain"][1] for p in seen)
    assert seen[0][0] == seen[1][0]  # one layer for the whole video
    seen.clear()  # no weather in the script: the faintest slow dust, so it's never just a picture
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=cv.parse_script(SCRIPT)))
    assert [p[1] for p in seen] == [cv.STILL_AIR[1]] * 2
    assert all(kind in cv.PARTICLES for kind in cv.AMBIENCE)  # every world the script can pick has its own
    seen.clear()  # another look: nothing drifts
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert seen == [None] * 2
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (5, 5, 5)).save(still)
    layer = cv.particle_tile("dust", tmp_path / "p.png", seed=1)
    cv.render_scene([still], None, 1.0, tmp_path / "p.mp4", hit="boom", riser=True, particles=(layer, 600))

    def frame(n):
        out = tmp_path / f"f{n}.png"
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / "p.mp4"), "-vf", f"select=eq(n\\,{n})", "-frames:v", "1",
                        str(out)], check=True, capture_output=True)
        return Image.open(out).convert("L")
    a, b = frame(12), frame(24)
    assert a.getextrema()[1] > 60 and a.tobytes() != b.tobytes()  # specks show, and they move
    assert abs(cv.audio_seconds(tmp_path / "p.mp4") - 1.0) < 0.15


def test_lore_closeups_pull_into_focus(s, tmp_path, monkeypatch):
    script = cv.parse_script(SCRIPT)
    seen = []

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        seen.append(a[13]), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert seen == [True, True, False, False]
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image, ImageFilter, ImageStat
    wide, close, flash = tmp_path / "w.png", tmp_path / "c.png", tmp_path / "f.png"
    Image.new("RGB", (cv.W, cv.H), (40, 40, 40)).save(wide)
    Image.new("RGB", (cv.W, cv.H), (200, 30, 30)).save(flash)
    board = Image.new("RGB", (cv.W, cv.H), (0, 0, 0))
    for y in range(0, cv.H, 40):
        for x in range((y // 40) % 2 * 40, cv.W, 80):
            board.paste((255, 255, 255), (x, y, x + 40, y + 40))
    board.save(close)

    def sharpness(video, n):
        out = tmp_path / f"{video.stem}{n}.png"
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(video), "-vf", f"select=eq(n\\,{n})", "-frames:v", "1", str(out)],
                       check=True, capture_output=True)
        return ImageStat.Stat(Image.open(out).convert("L").filter(ImageFilter.FIND_EDGES)).stddev[0]
    cv.render_scene([wide, close], None, 2.0, tmp_path / "pull.mp4", focus=True, teaser=flash)
    cv.render_scene([wide, close], None, 2.0, tmp_path / "flat.mp4", teaser=flash)
    start = round(2.0 * cv.FPS * 0.55) + 1  # the closeup's second frame
    assert sharpness(tmp_path / "pull.mp4", start) < 0.6 * sharpness(tmp_path / "pull.mp4", start + 25)  # soft, then sharp
    assert sharpness(tmp_path / "flat.mp4", start) > 0.8 * sharpness(tmp_path / "flat.mp4", start + 25)  # no pull: sharp


def test_rain_stories_get_lightning_and_thunder(s, tmp_path, monkeypatch):
    lengths = [5.0] * 11
    played = [""] * 11
    played[6] = "boom"
    assert cv.storm_times(lengths, played) == {2: 2.0, 10: 2.0}  # every 4th from the third, never over a hit
    assert cv.storm_times([5.0, 5.0, 0.5], ["", "", ""]) == {}  # no room for the thunder before the cut
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "ambience": "rain"}))
    script["scenes"] = [dict(script["scenes"][i % 2]) for i in range(4)]
    seen = {}

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        seen.__setitem__(a[1], a[14]), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "add_ambience", lambda video, kind, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "make_score", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert seen[2] is not None and all(seen[i] is None for i in (0, 1, 3))
    seen.clear()  # a dry story, or another look: no storm
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script={**script, "ambience": "night"}))
    assert set(seen.values()) == {None}
    seen.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert set(seen.values()) == {None}
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import re
    import subprocess
    from PIL import Image, ImageStat
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (40, 40, 50)).save(still)
    cv.render_scene([still], None, 2.0, tmp_path / "storm.mp4", storm=0.5)

    def bright(n):
        out = tmp_path / f"b{n}.png"
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / "storm.mp4"), "-vf", f"select=eq(n\\,{n})", "-frames:v",
                        "1", str(out)], check=True, capture_output=True)
        return ImageStat.Stat(Image.open(out).convert("L")).mean[0]
    assert bright(round(0.52 * cv.FPS)) > bright(round(0.3 * cv.FPS)) + 40  # the flash
    assert abs(bright(round(1.5 * cv.FPS)) - bright(round(0.3 * cv.FPS))) < 5  # and back to the scene
    out = subprocess.run([cv.ffmpeg(), "-v", "info", "-ss", "1.2", "-t", "0.4", "-i", str(tmp_path / "storm.mp4"),
                          "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    assert float(re.search(r"max_volume: (-?[\d.]+)", out).group(1)) > -40  # the thunder rolls in after it


def test_lore_types_a_dateline_as_the_story_starts(s, tmp_path, monkeypatch):
    script = cv.parse_script(json.dumps({**json.loads(SCRIPT), "dateline": "Derry, Maine · Oct 1987"}))
    assert script["dateline"] == "DERRY, MAINE · OCT 1987"
    assert cv.parse_script(SCRIPT)["dateline"] == ""
    assert "dateline" in cv.SCRIPT_PROMPT
    seen = {}

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        seen.__setitem__(a[1], a[15]), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "add_ambience", lambda video, kind, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "make_score", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert seen[cv.DATELINE_SCENE] is not None and seen[cv.DATELINE_SCENE][1] > 0  # only on the first story scene
    assert all(v is None for i, v in seen.items() if i != cv.DATELINE_SCENE)
    seen.clear()  # no dateline in the script, or another look: nothing typed
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script={**script, "dateline": ""}))
    assert set(seen.values()) == {None}
    seen.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert set(seen.values()) == {None}
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import re
    import subprocess
    from PIL import Image, ImageStat
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (40, 40, 50)).save(still)
    stamp = cv.dateline_image("DERRY, MAINE · OCT 1987", tmp_path / "d.png")
    width = Image.open(stamp[0]).size[0]
    cv.render_scene([still], None, 5.0, tmp_path / "typed.mp4", dateline=stamp)

    def band(n, left=0.0, right=1.0):
        out = tmp_path / f"d{n}.png"
        x = cv.SAFE_SIDE + int(width * left)
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / "typed.mp4"), "-vf",
                        f"select=eq(n\\,{n}),crop={int(width * (right - left))}:{cv.DATELINE_H}:{x}:{cv.DATELINE_Y}",
                        "-frames:v", "1", str(out)], check=True, capture_output=True)
        return Image.open(out).convert("L").getextrema()[1]
    assert band(2) < 80  # nothing typed yet
    mid = round((cv.DATELINE_AT + stamp[1] / 2) * cv.FPS)
    assert band(mid, 0.0, 0.3) > 200 and band(mid, 0.75, 1.0) < 80  # half typed: the start shows, the end doesn't
    assert band(round(2.5 * cv.FPS)) > 200  # all there
    assert band(round(4.8 * cv.FPS)) < 80  # and gone again
    out = subprocess.run([cv.ffmpeg(), "-v", "info", "-ss", "0.3", "-t", "1", "-i", str(tmp_path / "typed.mp4"),
                          "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    assert float(re.search(r"max_volume: (-?[\d.]+)", out).group(1)) > -40  # the typewriter taps


def test_lore_twists_drain_the_colour(s, tmp_path, monkeypatch):
    script = cv.parse_script(SCRIPT)
    script["scenes"] = [dict(script["scenes"][i % 2], hit="") for i in range(4)]
    script["scenes"][2]["hit"] = "boom"
    seen = {}

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        seen.__setitem__(a[1], a[16]), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "add_ambience", lambda video, kind, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "make_score", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert seen == {0: False, 1: False, 2: True, 3: False}  # only the boom reveal
    seen.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert set(seen.values()) == {False}
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import subprocess
    from PIL import Image, ImageStat
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (200, 40, 40)).save(still)
    cv.render_scene([still], None, 3.0, tmp_path / "drain.mp4", drain=True)

    def colour(n):
        out = tmp_path / f"c{n}.png"
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / "drain.mp4"), "-vf", f"select=eq(n\\,{n})", "-frames:v",
                        "1", str(out)], check=True, capture_output=True)
        return ImageStat.Stat(Image.open(out).convert("HSV")).mean[1]
    grey, back = colour(round(0.5 * cv.FPS)), colour(round(2.6 * cv.FPS))
    assert grey < 0.35 * back  # grey as the twist lands, the colour back once it has sunk in


def test_lore_punch_words_land_with_a_thump(s, tmp_path, monkeypatch):
    words = [(0.1, 0.4, "She"), (0.4, 0.9, "found"), (0.9, 1.3, "room"), (1.6, 2.0, "4B."), (2.2, 2.6, "Room"),
             (2.7, 3.0, "4B"), (3.1, 3.4, "again")]
    assert cv.thump_times(words, ["room", "4b"]) == [0.9, 1.6]  # first time each is said, at most two
    assert cv.thump_times(words, ["room", "4b"], hit="boom") == [1.6, 2.2]  # clear of the boom ringing out
    assert cv.thump_times(words, []) == []
    script = cv.parse_script(SCRIPT)
    script["scenes"] = [dict(script["scenes"][i % 2], hit="") for i in range(3)]
    script["scenes"][1]["punch"] = [cv.bare(script["scenes"][1]["narration"].split()[1])]
    script["scenes"][0]["punch"] = script["scenes"][2]["punch"] = []
    seen = {}

    async def no_picture(*a, **k):
        return None

    async def a_voice(http, settings, text, voice, target, *a, **k):
        target.write_bytes(b"mp3")
        return True
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", a_voice)
    monkeypatch.setattr(cv, "audio_seconds", lambda path: 4.0)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        seen.__setitem__(a[1], a[17]), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "add_ambience", lambda video, kind, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "make_score", lambda *a: None)
    monkeypatch.setattr(cv, "normalise", lambda video, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    monkeypatch.setattr(cv, "video_facts", lambda path: "")
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert seen[0] == [] and seen[2] == [] and len(seen[1]) == 1 and seen[1][0] > 0
    seen.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert set(map(tuple, seen.values())) == {()}
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import re
    import subprocess
    from PIL import Image
    still = tmp_path / "s.png"
    Image.new("RGB", (cv.W, cv.H), (40, 40, 50)).save(still)
    cv.render_scene([still], None, 2.0, tmp_path / "thump.mp4", thumps=[1.0])

    def peak(at):
        out = subprocess.run([cv.ffmpeg(), "-v", "info", "-ss", str(at), "-t", "0.3", "-i", str(tmp_path / "thump.mp4"),
                              "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
        return float(re.search(r"max_volume: (-?[\d.]+)", out).group(1))
    assert peak(1.0) > -30 and peak(0.3) < -60  # the thump lands on the word, silence before it


def test_lore_rewinds_the_tape_after_the_flash_forward(s, tmp_path, monkeypatch):
    script = cv.parse_script(SCRIPT)
    script["scenes"] = [dict(script["scenes"][i % 2], hit="") for i in range(4)]
    seen = {}

    async def no_picture(*a, **k):
        return None

    async def no_voice(*a, **k):
        return False
    monkeypatch.setattr(cv, "fetch_picture", no_picture)
    monkeypatch.setattr(cv, "narrate", no_voice)
    monkeypatch.setattr(cv, "render_scene", lambda stills, audio, seconds, out, *a: (
        seen.__setitem__(a[1], a[18]), out.write_bytes(b"mp4")))
    monkeypatch.setattr(cv, "join", lambda parts, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "add_ambience", lambda video, kind, out: out.write_bytes(b"mp4"))
    monkeypatch.setattr(cv, "music_for", lambda *a: None)
    monkeypatch.setattr(cv, "make_score", lambda *a: None)
    monkeypatch.setattr(cv, "check_video", lambda path: [])
    lore = cs.account(cs.load(s), "lowkey.lore")
    asyncio.run(cv.make(None, None, s, lore, tmp_path, script=script))
    assert seen == {0: True, 1: False, 2: False, 3: False}  # only the opening scene
    seen.clear()
    asyncio.run(cv.make(None, None, s, {**lore, "style": "noir"}, tmp_path, script=script))
    assert set(seen.values()) == {False}
    monkeypatch.undo()
    pytest.importorskip("imageio_ffmpeg")
    import re
    import subprocess
    from PIL import Image, ImageStat
    still, later = tmp_path / "s.png", tmp_path / "t.png"
    Image.new("RGB", (cv.W, cv.H), (200, 60, 60)).save(still)
    Image.new("RGB", (cv.W, cv.H), (60, 60, 200)).save(later)
    for name, rewind in (("tape", True), ("plain", False)):
        cv.render_scene([still], None, 2.0, tmp_path / f"{name}.mp4", teaser=later, rewind=rewind)

    def colour(name, n):
        out = tmp_path / f"{name}{n}.png"
        subprocess.run([cv.ffmpeg(), "-y", "-i", str(tmp_path / f"{name}.mp4"), "-vf", f"select=eq(n\\,{n})",
                        "-frames:v", "1", str(out)], check=True, capture_output=True)
        return ImageStat.Stat(Image.open(out).convert("HSV")).mean[1]
    during = round((cv.TEASER_SECONDS + 0.1) * cv.FPS)
    assert colour("tape", during) < 0.75 * colour("plain", during)  # the picture judders, washed out
    assert abs(colour("tape", round(1.5 * cv.FPS)) - colour("plain", round(1.5 * cv.FPS))) < 8  # then it's clean

    def peak(name):
        out = subprocess.run([cv.ffmpeg(), "-v", "info", "-ss", str(cv.TEASER_SECONDS), "-t", "0.3", "-i",
                              str(tmp_path / f"{name}.mp4"), "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        return float(re.search(r"max_volume: (-?[\d.]+)", out).group(1))
    assert peak("tape") > -30 and peak("plain") < -60  # the tape whirr
