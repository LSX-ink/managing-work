import asyncio

import play
import tools
from config import Settings


def test_clean_query():
    assert play.clean_query("play some Drake on Spotify please") == "Drake"
    assert play.clean_query("Alfred, play Blinding Lights") == "Blinding Lights"
    assert play.clean_query("put on lo-fi beats") == "lo-fi beats"


def test_videos_go_to_youtube():
    assert play.is_video("the Arsenal highlights")
    assert play.is_video("a cooking video")
    assert not play.is_video("Blinding Lights")


def test_first_video():
    assert play.first_video('..."videoId":"4NRXx6U8ABQ","x"..."videoId":"fHI8X4OXluQ"') == "4NRXx6U8ABQ"
    assert play.first_video("<html></html>") is None


def test_pick_play_button_skips_the_player_bar():
    assert play.pick_play_button(["Play", "Next", "More options for Blinding Lights", "Play",
                                  "Play Blinding Lights"]) == 3
    assert play.pick_play_button(["Play", "Play Blinding Lights"]) == 1
    assert play.pick_play_button(["Play", "Pause"]) is None


def test_youtube_opens_the_video(monkeypatch):
    opened = []
    monkeypatch.setattr(play.webbrowser, "open", opened.append)
    monkeypatch.setattr(play, "spotify_installed", lambda: False)

    class Http:
        async def get(self, *a, **k):
            return type("R", (), {"text": '"videoId":"4NRXx6U8ABQ"'})()

    out = asyncio.run(play.run_tool("play", {"query": "play Blinding Lights"}, Settings(), Http()))
    assert opened == ["https://www.youtube.com/watch?v=4NRXx6U8ABQ"] and "Playing" in out


def test_registered_always_loaded():
    defs = {t["name"]: t for t in tools.client_tool_definitions(Settings())}
    assert "play" in defs and not defs["play"].get("defer_loading")
