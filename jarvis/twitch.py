"""Finding viral Twitch clips with Twitch's official API (Helix), ranked by views.

Setup (once): make a free app at dev.twitch.tv/console (any name, redirect http://localhost, category "Other"),
then put its Client ID and a new Client Secret in .env as TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET.
Alfred signs in as the app itself (no Twitch login needed) and only reads public clips.
"""

import random
import time
from datetime import datetime, timedelta, timezone

import httpx

from config import Settings

API = "https://api.twitch.tv/helix"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"
_token: dict = {"value": "", "until": 0.0}
# Where "old viral" clips come from: a random week within this many days back.
OLD_DAYS = 3 * 365


def configured(settings: Settings) -> bool:
    return bool(settings.twitch_client_id and settings.twitch_client_secret)


def setup_line() -> str:
    return ("To find clips, Alfred needs a free Twitch app: make one at dev.twitch.tv/console, then put its Client ID "
            "and Client Secret in .env as TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET and restart.")


async def token(http: httpx.AsyncClient, settings: Settings) -> str:
    if _token["value"] and _token["until"] > time.time():
        return _token["value"]
    if not configured(settings):
        raise ValueError(setup_line())
    resp = await http.post(TOKEN_URL, data={"client_id": settings.twitch_client_id,
                                            "client_secret": settings.twitch_client_secret,
                                            "grant_type": "client_credentials"})
    body = resp.json()
    if "access_token" not in body:
        raise ValueError(f"Twitch said: {body.get('message') or resp.status_code}")
    _token.update(value=body["access_token"], until=time.time() + int(body.get("expires_in", 3600)) - 60)
    return _token["value"]


async def get(http: httpx.AsyncClient, settings: Settings, path: str, params: dict) -> list[dict]:
    headers = {"Client-Id": settings.twitch_client_id, "Authorization": f"Bearer {await token(http, settings)}"}
    resp = await http.get(f"{API}/{path}", params=params, headers=headers)
    if resp.status_code == 401:  # the token ran out early; get a new one once
        _token["value"] = ""
        headers["Authorization"] = f"Bearer {await token(http, settings)}"
        resp = await http.get(f"{API}/{path}", params=params, headers=headers)
    if resp.status_code != 200:
        raise ValueError(f"Twitch answered {resp.status_code}.")
    return resp.json().get("data") or []


async def user_ids(http: httpx.AsyncClient, settings: Settings, logins: list[str]) -> dict[str, str]:
    """{login: id} for up to 100 streamer names."""
    if not logins:
        return {}
    found = await get(http, settings, "users", [("login", name.lower().lstrip("@")) for name in logins[:100]])
    return {u["login"]: u["id"] for u in found}


async def video_views(http: httpx.AsyncClient, settings: Settings, ids: list[str]) -> dict[str, int]:
    """{video id: total views} for past streams (VODs). Streams Twitch has deleted are simply missing."""
    ids = list(dict.fromkeys(str(i) for i in ids if i))[:100]
    if not ids:
        return {}
    try:
        found = await get(http, settings, "videos", [("id", i) for i in ids])
    except ValueError:  # one deleted stream can fail the whole batch: ask one by one
        found = []
        for i in ids[:20]:
            try:
                found += await get(http, settings, "videos", {"id": i})
            except ValueError:
                pass
    return {str(v["id"]): int(v.get("view_count") or 0) for v in found if v.get("id")}


async def game_id(http: httpx.AsyncClient, settings: Settings, name: str) -> str:
    found = await get(http, settings, "games", {"name": name})
    if not found:
        raise ValueError(f"Twitch has no category called {name}.")
    return found[0]["id"]


def window(era: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    """(start, end) of the time to search: 'new' is the last 7 days, 'old' a random week in the last few years."""
    now = now or datetime.now(timezone.utc)
    if era == "new":
        return now - timedelta(days=7), now
    start = now - timedelta(days=random.randint(30, OLD_DAYS))
    return start, start + timedelta(days=7)


async def top_clips(http: httpx.AsyncClient, settings: Settings, era: str, broadcasters: list[str] | None = None,
                    category: str = "Just Chatting", count: int = 40) -> list[dict]:
    """The most-viewed clips in the window, from the given streamers or else the category, newest API fields kept."""
    start, end = window(era)
    base = {"first": min(100, count), "started_at": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ended_at": end.strftime("%Y-%m-%dT%H:%M:%SZ")}
    clips: list[dict] = []
    if broadcasters:
        ids = await user_ids(http, settings, broadcasters)
        for bid in ids.values():
            clips += await get(http, settings, "clips", {**base, "broadcaster_id": bid})
    else:
        clips = await get(http, settings, "clips", {**base, "game_id": await game_id(http, settings, category)})
    return sorted(clips, key=lambda c: c.get("view_count", 0), reverse=True)
