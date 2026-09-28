"""Shared helpers for the web-in-Alfred abilities: safe fetching, RSS feeds, place names and links.

Only keyless, read-only public services are used, and only a search word or a place name is ever sent.
Links that come from the user or from a web page are checked with memory.check_public on every hop.
"""

import html
import math
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import httpx

import feeds
import memory

TIMEOUT = 10
HEADERS = {"User-Agent": "Alfred-assistant/1.0"}
MAX_PAGE = 3 * 1024 * 1024
MAX_FEED = 12 * 1024 * 1024
GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
ITUNES = "https://itunes.apple.com/search"
ITUNES_NS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"


def clean(value, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))).strip()[:limit]


def need(value, what: str, limit: int = 100) -> str:
    text = clean(value, limit)
    if not text:
        raise ValueError(f"Say which {what}.")
    return text


def https(url) -> str:
    """The link if it is https, else empty (the screen only shows https pictures and sound)."""
    url = str(url or "").strip()
    return url if url.startswith("https://") and len(url) < 2000 else ""


async def get_json(http: httpx.AsyncClient, url: str, what: str, params: dict | None = None, missing: str | None = None):
    return await feeds.fetch_json(http, url, what, params, missing)


async def get_public(http: httpx.AsyncClient, url: str, what: str = "web page", limit: int = MAX_PAGE) -> httpx.Response:
    """GET a link from the user or a web page, re-checking it is public after every redirect."""
    url = str(url or "").strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    for _ in range(6):
        await memory.check_public(url)
        try:
            r = await http.get(url, follow_redirects=False, timeout=TIMEOUT,
                               headers={"User-Agent": "Mozilla/5.0 Alfred-assistant"})
        except httpx.HTTPError:
            raise ValueError(f"The {what} isn't answering right now.") from None
        if r.is_redirect:
            url = urljoin(url, r.headers["location"])
            continue
        if r.status_code != 200:
            raise ValueError(f"The {what} answered {r.status_code}.")
        if len(r.content) > limit:
            raise ValueError(f"That {what} is too big to read.")
        return r
    raise ValueError("That link redirected too many times.")


def parse_feed(text: str) -> tuple[dict, list[dict]]:
    """(channel info, items) of an RSS feed. Refuses DTDs and entities, like feeds.parse_rss."""
    if len(text) > MAX_FEED or re.search(r"<!\s*(DOCTYPE|ENTITY)", text, re.I):
        raise ValueError("That feed looked unsafe, so I didn't read it.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise ValueError("That feed came back garbled.") from None
    channel = root.find("channel")
    info = {"title": clean(channel.findtext("title") if channel is not None else "", 120), "image": ""}
    if channel is not None:
        art = channel.find(f"{ITUNES_NS}image")
        info["image"] = https(art.get("href") if art is not None else channel.findtext("image/url"))
    items = []
    for item in root.iter("item"):
        title = clean(item.findtext("title"), 200)
        if not title:
            continue
        enclosure = item.find("enclosure")
        items.append({"title": title, "link": https(item.findtext("link")) or clean(item.findtext("link"), 500),
                      "description": clean(item.findtext("description"), 300),
                      "date": clean(item.findtext("pubDate"), 40),
                      "audio": https(enclosure.get("url")) if enclosure is not None else ""})
    return info, items


async def geocode(http: httpx.AsyncClient, place) -> dict:
    """{name, label, lat, lon, kind} for a place name, from Open-Meteo's keyless geocoder."""
    place = need(place, "place", 100)
    body = await get_json(http, GEOCODE, "place finder", {"name": place, "count": 1, "language": "en", "format": "json"})
    found = (body.get("results") or [None])[0] if isinstance(body, dict) else None
    if not found:
        raise ValueError(f"I couldn't find a place called {place}.")
    label = ", ".join(x for x in (found.get("name"), found.get("admin1"), found.get("country")) if x)
    return {"name": found.get("name") or place, "label": label, "lat": float(found["latitude"]),
            "lon": float(found["longitude"]), "kind": found.get("feature_code") or ""}


def haversine_km(a: dict, b: dict) -> float:
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat, dlon = lat2 - lat1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def meta(markup: str, *keys: str) -> str:
    """The content of the first <meta property/name=key> found, in key order."""
    for key in keys:
        for pattern in (rf'<meta[^>]+(?:property|name)=["\']{key}["\'][^>]+content=["\']([^"\']*)',
                        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{key}["\']'):
            m = re.search(pattern, markup, re.I)
            if m and m.group(1).strip():
                return html.unescape(m.group(1)).strip()
    return ""
