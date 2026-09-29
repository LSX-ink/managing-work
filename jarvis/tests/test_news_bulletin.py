import asyncio

import httpx
import pytest

import memory
import news_bulletin
import tools
from config import Settings

FEED = """<?xml version="1.0"?><rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>
<title>Global News Podcast</title><itunes:image href="https://img.test/gnp.jpg"/>
<item><title>Storm hits coast</title><pubDate>Tue, 29 Sep 2026 05:00:00 GMT</pubDate>
<enclosure url="https://audio.test/gnp-latest.mp3" type="audio/mpeg"/></item>
<item><title>Yesterday</title><enclosure url="https://audio.test/gnp-old.mp3" type="audio/mpeg"/></item>
</channel></rss>"""
TOP = """<?xml version="1.0"?><rss version="2.0"><channel><title>BBC</title>
<item><title>One</title></item><item><title>Two</title></item><item><title>Three</title></item><item><title>Four</title></item>
</channel></rss>"""
searched = []


def handler(request: httpx.Request) -> httpx.Response:
    host, q = request.url.host, request.url.params
    if host == "itunes.apple.com":
        searched.append(q["term"])
        return httpx.Response(200, json={"results": [
            {"collectionName": "Fake news pod", "artistName": "Someone else", "feedUrl": "https://fake.test/x.xml"},
            {"collectionName": q["term"], "artistName": "BBC World Service" if "Global" in q["term"] else "NPR",
             "feedUrl": "https://podcasts.test/feed.xml"}]})
    if host == "podcasts.test":
        return httpx.Response(200, text=FEED)
    if host == "feeds.bbci.co.uk":
        return httpx.Response(200, text=TOP)
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def public_links(monkeypatch):
    async def ok(url):
        return None
    monkeypatch.setattr(memory, "check_public", ok)


def call(args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await news_bulletin.run_tool("news_bulletin", args, Settings(), http)
    return asyncio.run(go())


def test_play_todays_news_plays_the_newest_bbc_bulletin_headlines_first():
    out = call({})
    d = out.card["data"]
    assert out == "Here's the latest from BBC World Service."
    assert out.card["kind"] == "radio" and d["autoplay"] == 0 and d["wait_speech"] is True
    assert d["tracks"][0]["src"] == "https://audio.test/gnp-latest.mp3"
    assert d["stop_after"] == 100 and d["headlines"] == ["One", "Two", "Three"]
    assert out.card["buttons"][0]["say"] == "Play the full BBC World Service news bulletin."
    assert searched[-1] == "Global News Podcast"


def test_full_bulletin_and_other_stations():
    full = call({"full": True})
    assert full.card["data"]["stop_after"] == 0 and full.card["buttons"] == []
    assert call({"station": "npr"}) == "Here's the latest from NPR News."
    assert news_bulletin.station_key("World Service") == "bbc" and news_bulletin.station_key("bbc minute") == "bbc_minute"


def test_news_bulletin_is_an_ability():
    assert news_bulletin in tools.ABILITIES
    assert "news_bulletin" in {t["name"] for t in news_bulletin.tool_definitions()}
