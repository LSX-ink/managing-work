import httpx
import pytest

import music
import tools
from config import Settings

SETTINGS = Settings(speech_lang="en-GB", music_country="", enable_pc=True)


@pytest.mark.parametrize(
    "lang, override, expected",
    [("en-GB", "", "gb"), ("af-ZA", "", "za"), ("en", "", "us"), ("en-GB", "ZA", "za")],
)
def test_country(lang, override, expected):
    assert music.country(Settings(speech_lang=lang, music_country=override)) == expected


def fake_http(results, seen):
    def handler(request):
        seen.append(request.url)
        return httpx.Response(200, json={"resultCount": len(results), "results": results})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_find_song():
    seen = []
    song = {"trackName": "Bohemian Rhapsody", "artistName": "Queen",
            "trackViewUrl": "https://music.apple.com/gb/album/x/1?i=2"}
    async with fake_http([song], seen) as http:
        hit = await music.find(http, SETTINGS, "bohemian rhapsody")
    assert hit == {"name": "Bohemian Rhapsody", "by": "Queen", "url": "https://music.apple.com/gb/album/x/1?i=2"}
    assert seen[0].params["entity"] == "song" and seen[0].params["country"] == "gb"


async def test_find_artist_and_nothing():
    seen = []
    artist = {"artistName": "Adele", "artistLinkUrl": "https://music.apple.com/gb/artist/adele/1"}
    async with fake_http([artist], seen) as http:
        assert (await music.find(http, SETTINGS, "adele", "artist"))["name"] == "Adele"
    assert seen[0].params["entity"] == "musicArtist"
    async with fake_http([], seen) as http:
        assert "Nothing on Apple Music" in await music.apple_music(http, SETTINGS, "zzzz")


async def test_apple_music_opens_the_link(monkeypatch):
    opened = []
    monkeypatch.setattr(music, "open_in_app", lambda url: opened.append(url) or "the Apple Music app")
    song = {"trackName": "Hello", "artistName": "Adele", "trackViewUrl": "https://music.apple.com/gb/song/1"}
    async with fake_http([song], []) as http:
        out = await tools.run_tool("apple_music", {"query": "hello adele"}, SETTINGS, http)
    assert opened == ["https://music.apple.com/gb/song/1"]
    assert out.startswith("Opened Hello by Adele in the Apple Music app")


def test_tool_only_with_pc_control():
    names = lambda s: [t["name"] for t in tools.client_tool_definitions(s)]
    assert "apple_music" in names(SETTINGS)
    assert "apple_music" not in names(Settings(enable_pc=False))
