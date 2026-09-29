"""Posting to TikTok with TikTok's official Content Posting API, only after the user approves each video.

Setup (once): make a free app at developers.tiktok.com, add Login Kit and Content Posting API, add the redirect
address http://localhost:8340/tiktok/callback, and put its Client key and Client secret in .env as
TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET. Then press "Connect" beside each account on Alfred's studio card and
log in to that TikTok account.

Two ways to post (JARVIS_TIKTOK_MODE):
  draft  (default) the video lands in your TikTok inbox; open TikTok, add a sound if you like, tick
         "AI-generated content" and press Post. Works for any app.
  direct the video posts straight away, marked as AI-generated. TikTok only allows public direct posts once
         it has approved (audited) your app; until then they post as private ("only me").
Tokens are kept per account in .tiktok-tokens.json in the memory folder, which never leaves this PC.
"""

import hashlib
import json
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx

import memory
from config import Settings

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
API = "https://open.tiktokapis.com/v2"
SCOPES = "user.info.basic,video.upload,video.publish,video.list"
TOKENS = ".tiktok-tokens.json"
ONE_CHUNK = 64 * 1024 * 1024
CHUNK = 10 * 1024 * 1024
_pending: dict[str, dict] = {}  # login state -> {account, verifier, at}


def configured(settings: Settings) -> bool:
    return bool(settings.tiktok_client_key and settings.tiktok_client_secret)


def setup_line() -> str:
    return ("To post by itself, Alfred needs a free TikTok developer app: add its Client key and secret to .env as "
            "TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET, restart, then press Connect beside each account.")


def redirect_uri(settings: Settings) -> str:
    return settings.tiktok_redirect_uri or f"http://localhost:{settings.port}/tiktok/callback"


def _path(settings: Settings) -> Path:
    return memory.root(settings) / TOKENS


def tokens(settings: Settings) -> dict:
    try:
        data = json.loads(_path(settings).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_tokens(settings: Settings, data: dict) -> None:
    _path(settings).parent.mkdir(parents=True, exist_ok=True)
    _path(settings).write_text(json.dumps(data, indent=2), encoding="utf-8")


def connected(settings: Settings, account: str) -> bool:
    t = tokens(settings).get(account) or {}
    return bool(t.get("refresh_token")) and t.get("refresh_expires_at", 0) > time.time()


def disconnect(settings: Settings, account: str) -> None:
    data = tokens(settings)
    data.pop(account, None)
    save_tokens(settings, data)


def login_url(settings: Settings, account: str) -> str:
    """The TikTok login page for one account (PKCE, as TikTok asks of desktop apps)."""
    if not configured(settings):
        raise ValueError(setup_line())
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = hashlib.sha256(verifier.encode()).hexdigest()  # TikTok's desktop PKCE uses the hex digest
    now = time.time()
    for key in [k for k, v in _pending.items() if now - v["at"] > 900]:
        _pending.pop(key, None)
    _pending[state] = {"account": account, "verifier": verifier, "at": now}
    return AUTH_URL + "?" + urlencode({
        "client_key": settings.tiktok_client_key, "response_type": "code", "scope": SCOPES,
        "redirect_uri": redirect_uri(settings), "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})


def _store(settings: Settings, account: str, body: dict) -> None:
    if "access_token" not in body:
        raise ValueError(f"TikTok said: {body.get('error_description') or body.get('error') or body}")
    now = time.time()
    data = tokens(settings)
    data[account] = {"access_token": body["access_token"], "refresh_token": body.get("refresh_token", ""),
                     "open_id": body.get("open_id", ""), "scope": body.get("scope", ""),
                     "expires_at": now + int(body.get("expires_in", 86400)) - 120,
                     "refresh_expires_at": now + int(body.get("refresh_expires_in", 31536000))}
    save_tokens(settings, data)


async def finish_login(http: httpx.AsyncClient, settings: Settings, state: str, code: str) -> str:
    """Swap the code TikTok sent back for tokens; returns the account name."""
    pending = _pending.pop(state or "", None)
    if not pending:
        raise ValueError("That TikTok login has expired. Press Connect again.")
    resp = await http.post(f"{API}/oauth/token/", data={
        "client_key": settings.tiktok_client_key, "client_secret": settings.tiktok_client_secret,
        "code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri(settings),
        "code_verifier": pending["verifier"]})
    _store(settings, pending["account"], resp.json())
    return pending["account"]


async def access_token(http: httpx.AsyncClient, settings: Settings, account: str) -> str:
    t = tokens(settings).get(account)
    if not t or not connected(settings, account):
        raise ValueError(f"{account} isn't connected to TikTok yet. Press Connect beside it on the studio card.")
    if t["expires_at"] > time.time():
        return t["access_token"]
    resp = await http.post(f"{API}/oauth/token/", data={
        "client_key": settings.tiktok_client_key, "client_secret": settings.tiktok_client_secret,
        "grant_type": "refresh_token", "refresh_token": t["refresh_token"]})
    _store(settings, account, resp.json())
    return tokens(settings)[account]["access_token"]


def _check(resp: httpx.Response) -> dict:
    try:
        body = resp.json()
    except ValueError:
        raise ValueError(f"TikTok answered {resp.status_code}.") from None
    err = body.get("error") or {}
    if resp.status_code >= 400 or (err.get("code") not in (None, "", "ok")):
        raise ValueError(f"TikTok said: {err.get('message') or err.get('code') or resp.status_code}")
    return body.get("data") or {}


def chunks(size: int) -> tuple[int, int]:
    """(chunk size, chunk count) as TikTok wants them: one chunk up to 64 MB, else 10 MB chunks (the last one bigger)."""
    if size <= ONE_CHUNK:
        return size, 1
    return CHUNK, size // CHUNK


async def post(http: httpx.AsyncClient, settings: Settings, account: str, video: Path, caption: str) -> dict:
    """Send one approved video to TikTok. Returns {publish_id, mode}."""
    token = await access_token(http, settings, account)
    auth = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    size = video.stat().st_size
    chunk, count = chunks(size)
    source = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count}
    mode = "direct" if settings.tiktok_mode == "direct" else "draft"
    if mode == "direct":
        info = _check(await http.post(f"{API}/post/publish/creator_info/query/", headers=auth, json={}))
        options = info.get("privacy_level_options") or ["SELF_ONLY"]
        privacy = settings.tiktok_privacy if settings.tiktok_privacy in options else (
            "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in options else options[0])
        body = {"post_info": {"title": caption[:2200], "privacy_level": privacy, "disable_comment": False,
                              "disable_duet": False, "disable_stitch": False, "video_cover_timestamp_ms": 1000,
                              "is_aigc": True},
                "source_info": source}
        data = _check(await http.post(f"{API}/post/publish/video/init/", headers=auth, json=body))
    else:
        data = _check(await http.post(f"{API}/post/publish/inbox/video/init/", headers=auth, json={"source_info": source}))
    upload_url, publish_id = data.get("upload_url"), data.get("publish_id")
    if not upload_url:
        raise ValueError("TikTok didn't give an upload address.")
    raw = video.read_bytes()
    for i in range(count):
        start = i * chunk
        end = size if i == count - 1 else start + chunk
        resp = await http.put(upload_url, content=raw[start:end], timeout=300, headers={
            "Content-Type": "video/mp4", "Content-Length": str(end - start),
            "Content-Range": f"bytes {start}-{end - 1}/{size}"})
        if resp.status_code not in (200, 201, 206):
            raise ValueError(f"TikTok upload stopped ({resp.status_code}).")
    return {"publish_id": publish_id, "mode": mode}


async def status(http: httpx.AsyncClient, settings: Settings, account: str, publish_id: str) -> str:
    token = await access_token(http, settings, account)
    data = _check(await http.post(f"{API}/post/publish/status/fetch/", json={"publish_id": publish_id},
                                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}))
    return str(data.get("status") or "unknown")



async def video_views(http: httpx.AsyncClient, settings: Settings, account: str) -> list[dict]:
    """The account's latest public videos with their view counts (needs the video.list permission)."""
    token = await access_token(http, settings, account)
    auth = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    found, cursor = [], None
    for _ in range(3):  # up to 60 videos
        body = {"max_count": 20, **({"cursor": cursor} if cursor else {})}
        data = _check(await http.post(f"{API}/video/list/?fields=id,title,video_description,view_count,create_time",
                                      headers=auth, json=body))
        found += data.get("videos") or []
        if not data.get("has_more"):
            break
        cursor = data.get("cursor")
    return found


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())[:60]


def match_views(found: list[dict], video: dict) -> int | None:
    """Views for one of our videos: by TikTok's post id when we have it, else by the start of its caption."""
    for item in found:
        if video.get("post_id") and str(item.get("id")) == str(video["post_id"]):
            return int(item.get("view_count") or 0)
    start = _norm(video.get("caption"))[:40]
    for item in found:
        text = _norm(item.get("video_description") or item.get("title"))
        if start and text.startswith(start):
            video["post_id"] = str(item.get("id"))
            return int(item.get("view_count") or 0)
    return None
