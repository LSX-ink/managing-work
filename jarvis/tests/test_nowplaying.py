import nowplaying

SONG = {"title": "Bohemian Rhapsody", "artist": "Queen", "album": "A Night at the Opera", "art": ""}


def test_changed_only_for_a_new_song():
    assert nowplaying.changed(None, SONG)
    assert not nowplaying.changed(SONG, dict(SONG, art="data:image/png;base64,xx"))  # same song
    assert not nowplaying.changed(SONG, None)  # paused or stopped
    assert nowplaying.changed(SONG, dict(SONG, title="Killer Queen"))


async def test_watch_does_nothing_off_windows(monkeypatch):
    monkeypatch.setattr(nowplaying.sys, "platform", "linux")
    shown = []

    async def show(song):
        shown.append(song)

    await nowplaying.watch(show)
    assert shown == []


def test_now_playing_reaches_open_pages(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    from fastapi.testclient import TestClient

    import server

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws", headers={"origin": "http://testserver"}) as ws:
            ws.receive_json()  # the notifications list
            client.portal.call(server.broadcast, server.app, {"type": "nowplaying", **SONG})
            assert ws.receive_json() == {"type": "nowplaying", **SONG}
