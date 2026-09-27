"""Apple Music: find a song, album, artist or playlist and open it in the Apple Music app.

Searching uses Apple's free iTunes Search API, so no Apple account or developer key is needed.
Play, pause, skip and volume use the media keys in pc.py, which the Apple Music app obeys.
"""

import os
import subprocess
import sys
import webbrowser

import httpx

from config import Settings

KINDS = {  # what to look for -> (iTunes entity, field holding the Apple Music link)
    "song": ("song", "trackViewUrl"),
    "album": ("album", "collectionViewUrl"),
    "artist": ("musicArtist", "artistLinkUrl"),
}


def tool_definition() -> dict:
    return {
        "name": "apple_music",
        "description": "Find a song, album or artist on Apple Music and open it in the user's Apple Music app, "
                       "ready to play. For play, pause, skip and volume use media_control instead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to find, e.g. 'Bohemian Rhapsody Queen'."},
                "kind": {"type": "string", "enum": list(KINDS), "description": "Default: song."},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }


def country(settings: Settings) -> str:
    """Apple Music store country: JARVIS_MUSIC_COUNTRY, else the region of the speech language (en-GB -> gb)."""
    if settings.music_country:
        return settings.music_country.lower()
    parts = settings.speech_lang.replace("_", "-").split("-")
    return parts[1].lower() if len(parts) > 1 and len(parts[1]) == 2 else "us"


async def find(http: httpx.AsyncClient, settings: Settings, query: str, kind: str = "song") -> dict | None:
    """The best match as {'name', 'by', 'url'}, or None."""
    entity, link = KINDS.get(kind, KINDS["song"])
    response = await http.get("https://itunes.apple.com/search", params={
        "term": query, "media": "music", "entity": entity, "limit": 1, "country": country(settings),
    })
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results or not results[0].get(link):
        return None
    hit = results[0]
    name = hit.get("trackName") or hit.get("collectionName") or hit.get("artistName", "")
    by = hit.get("artistName", "") if kind != "artist" else ""
    return {"name": name, "by": by, "url": hit[link]}


APP_SCHEMES = ("musics", "music", "itmss")  # link types the Apple Music (or iTunes) app may register


def windows_music_scheme() -> str | None:
    """The first Apple Music link type registered on this PC, if the app is installed."""
    import winreg

    for scheme in APP_SCHEMES:
        try:
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, scheme))
            return scheme
        except OSError:
            continue
    return None


def open_in_app(url: str) -> str:
    """Open an Apple Music link in the app when it's installed, otherwise in the browser."""
    if sys.platform == "win32":
        if scheme := windows_music_scheme():
            os.startfile(url.replace("https", scheme, 1))
            return "the Apple Music app"
    elif sys.platform == "darwin":
        subprocess.Popen(["open", url.replace("https://", "music://", 1)])
        return "the Music app"
    webbrowser.open(url)
    return "the browser"


async def apple_music(http: httpx.AsyncClient, settings: Settings, query: str, kind: str = "song") -> str:
    hit = await find(http, settings, query, kind)
    if not hit:
        return f"Nothing on Apple Music matched {query!r}."
    where = open_in_app(hit["url"])
    by = f" by {hit['by']}" if hit["by"] else ""
    return (f"Opened {hit['name']}{by} in {where}. The page is open but not playing yet: "
            f"tell the user to press play there.")
