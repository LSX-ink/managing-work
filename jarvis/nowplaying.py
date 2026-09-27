"""Now playing: tell the page when a new song starts, for the pop-up card on the HUD.

Reads Windows' own media info (the same one the volume pop-up shows), so it works with
Apple Music, Spotify, a browser playing YouTube, or any player that reports its songs.
"""

import asyncio
import base64
import sys
from typing import Awaitable, Callable

Show = Callable[[dict], Awaitable[None]]
MAX_ART_BYTES = 2_000_000


def song_key(song: dict | None) -> tuple | None:
    return (song["title"], song["artist"]) if song else None


def changed(previous: dict | None, current: dict | None) -> bool:
    """A new song started playing (not a pause, and not the same song resuming)."""
    return current is not None and song_key(current) != song_key(previous)


async def _art(thumbnail) -> str:
    """The album cover as a data: URL, or "" when there is none."""
    from winrt.windows.storage.streams import DataReader

    if thumbnail is None:
        return ""
    stream = await thumbnail.open_read_async()
    size = int(stream.size)
    if not size or size > MAX_ART_BYTES:
        return ""
    reader = DataReader(stream)
    await reader.load_async(size)
    data = bytearray(size)
    reader.read_bytes(data)
    mime = stream.content_type or "image/png"
    return f"data:{mime};base64,{base64.b64encode(bytes(data)).decode()}"


async def current_song(manager) -> dict | None:
    """What Windows says is playing right now, or None when nothing is."""
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status

    session = manager.get_current_session()
    if session is None or session.get_playback_info().playback_status != Status.PLAYING:
        return None
    props = await session.try_get_media_properties_async()
    if props is None or not props.title:
        return None
    song = {"title": props.title, "artist": props.artist or "", "album": props.album_title or "", "art": ""}
    try:
        song["art"] = await _art(props.thumbnail)
    except Exception:  # some players give no cover, or one Windows can't read
        pass
    return song


async def watch(show: Show, every: float = 2.0) -> None:
    """Call show(song) each time a new song starts playing."""
    if sys.platform != "win32":
        return
    try:
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
    except ImportError:
        print("[jarvis] The now-playing card needs the winrt packages: pip install -r requirements.txt", flush=True)
        return
    manager = await Manager.request_async()
    previous = None
    while True:
        try:
            song = await current_song(manager)
            if changed(previous, song):
                await show(song)
            if song is not None:
                previous = song  # a pause keeps the last song, so resuming it doesn't pop up again
        except Exception as exc:
            print(f"[jarvis] Reading the current song failed: {exc}", flush=True)
        await asyncio.sleep(every)
