"""Finding viral Kick clips (and the stream they came from), for clip accounts like n3on.vault.

Kick's public API (api.kick.com) has no clips, so Alfred reads the same JSON the kick.com website reads, through
yt-dlp's own networking (it can look like a normal browser when curl_cffi is installed, which Kick often needs).
yt-dlp's Kick extractors then download the clips (kick.com/<channel>/clips/clip_...) and the past streams
(kick.com/<channel>/videos/<uuid>), so a clip can be cut again from its stream with extra time either side.
No keys are needed. If KICK_CLIENT_ID and KICK_CLIENT_SECRET are set (an app from kick.com/settings/developer),
the channel is checked with Kick's official API first, so a misspelt channel says so clearly.
"""

import json
import time
from datetime import datetime, timezone

from config import Settings

SITE = "https://kick.com/api/v2/channels/{slug}/{what}"
OFFICIAL = "https://api.kick.com/public/v1/channels"
TOKEN_URL = "https://id.kick.com/oauth/token"
_token: dict = {"value": "", "until": 0.0}


def configured(settings: Settings) -> bool:
    """Kick's official API keys (optional: clips are found without them)."""
    return bool(settings.kick_client_id and settings.kick_client_secret)


def get_json(url: str) -> dict | list:
    """kick.com JSON through yt-dlp's networking, looking like a browser when it can."""
    import yt_dlp
    from yt_dlp.networking import Request
    from yt_dlp.networking.impersonate import ImpersonateTarget
    headers = {"Accept": "application/json"}
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        try:
            resp = ydl.urlopen(Request(url, headers=headers, extensions={"impersonate": ImpersonateTarget()}))
        except Exception:  # no curl_cffi: try as a plain request
            resp = ydl.urlopen(Request(url, headers=headers))
        return json.loads(resp.read().decode("utf-8"))


def when(text) -> float | None:
    """Seconds since 1970 from Kick's times ('2025-01-02T03:04:05.000Z' or '2025-01-02 03:04:05')."""
    if not text:
        return None
    try:
        at = datetime.fromisoformat(str(text).replace("Z", "+00:00").replace(" ", "T"))
    except ValueError:
        return None
    return (at if at.tzinfo else at.replace(tzinfo=timezone.utc)).timestamp()


def clip_row(c: dict, slug: str) -> dict:
    """A Kick clip in the same shape as a Twitch one (id, broadcaster_name, title, url, duration, view_count)."""
    channel = c.get("channel") or {}
    name = channel.get("slug") or slug
    return {"id": str(c.get("id")), "platform": "kick", "broadcaster_name": channel.get("username") or name,
            "channel": name, "title": c.get("title") or "", "url": f"https://kick.com/{name}/clips/{c.get('id')}",
            "duration": float(c.get("duration") or 0), "view_count": int(c.get("views") or c.get("view_count") or 0),
            "created_at": c.get("created_at"), "started_at": c.get("started_at"),
            "livestream_id": str(c.get("livestream_id") or ""), "thumbnail_url": c.get("thumbnail_url")}


def vod_views(clip: dict, vods: list[dict]) -> int:
    """Total views of the past stream the clip came from, or 0 when Kick doesn't say."""
    for v in vods:
        if str(v.get("id")) == clip.get("livestream_id"):
            return int((v.get("video") or {}).get("views") or v.get("views") or 0)
    return 0


def vod_offset(clip: dict, vods: list[dict]) -> tuple[str, float, float] | None:
    """(stream url, where the clip starts in it, the stream's length) when the clip's stream is still up, else None."""
    start = when(clip.get("started_at"))
    made = when(clip.get("created_at"))
    if start is None or (made and not 0 <= made - start <= 900):  # started_at isn't the clip's own start
        return None
    for v in vods:
        if str(v.get("id")) != clip.get("livestream_id"):
            continue
        began = when(v.get("start_time") or v.get("created_at"))
        uuid = (v.get("video") or {}).get("uuid")
        length = float(v.get("duration") or 0) / 1000  # milliseconds
        offset = start - began if began else -1
        if uuid and 0 <= offset and (not length or offset < length):
            return f"https://kick.com/{clip['channel']}/videos/{uuid}", offset, length
    return None


async def check_channel(http, settings: Settings, slug: str) -> None:
    """With the official keys set, make sure the channel exists (a clear message if not)."""
    if not configured(settings):
        return
    if not _token["value"] or _token["until"] < time.time():
        resp = await http.post(TOKEN_URL, data={"client_id": settings.kick_client_id, "grant_type": "client_credentials",
                                                "client_secret": settings.kick_client_secret})
        body = resp.json()
        if "access_token" not in body:
            raise ValueError(f"Kick didn't accept KICK_CLIENT_ID and KICK_CLIENT_SECRET: {body.get('message') or resp.status_code}")
        _token.update(value=body["access_token"], until=time.time() + int(body.get("expires_in", 3600)) - 60)
    resp = await http.get(OFFICIAL, params={"slug": slug}, headers={"Authorization": f"Bearer {_token['value']}"})
    if resp.status_code == 200 and not (resp.json().get("data") or []):
        raise ValueError(f"Kick has no channel called {slug}.")


def top_clips(slug: str, era: str, pages: int = 3) -> list[dict]:
    """The channel's most-viewed clips: 'new' from the last week, 'old' from all time. Blocking (run in a thread)."""
    found, cursor = [], "0"
    for _ in range(pages):
        body = get_json(SITE.format(slug=slug, what="clips") + f"?cursor={cursor}&sort=view&time={'week' if era == 'new' else 'all'}")
        found += [clip_row(c, slug) for c in (body.get("clips") or []) if isinstance(c, dict)]
        cursor = body.get("nextCursor")
        if not cursor:
            break
    return sorted(found, key=lambda c: c["view_count"], reverse=True)


def vods(slug: str) -> list[dict]:
    """The channel's past streams still on Kick. Blocking."""
    body = get_json(SITE.format(slug=slug, what="videos"))
    return body if isinstance(body, list) else (body.get("data") or body.get("videos") or [])
