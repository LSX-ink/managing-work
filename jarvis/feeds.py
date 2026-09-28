"""Live information from keyless public feeds: news, Hacker News, Wikipedia, earthquakes, the ISS, crypto.

Everything is read-only. Only a section, a topic or a coin name is ever sent; nothing about the user.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from urllib.parse import quote, urlparse

import httpx

from config import Settings

TIMEOUT = 10
HEADERS = {"User-Agent": "Alfred-assistant/1.0"}
MAX_XML = 2_000_000

BBC = "https://feeds.bbci.co.uk"
SECTIONS = {
    "top": "/news/rss.xml", "world": "/news/world/rss.xml", "uk": "/news/uk/rss.xml",
    "technology": "/news/technology/rss.xml", "business": "/news/business/rss.xml", "sport": "/sport/rss.xml",
    "science": "/news/science_and_environment/rss.xml",
    "entertainment": "/news/entertainment_and_arts/rss.xml", "health": "/news/health/rss.xml",
}
HN = "https://hacker-news.firebaseio.com/v0"
WIKI = "https://en.wikipedia.org/api/rest_v1"
USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary"
ISS_NOW = "http://api.open-notify.org/iss-now.json"
ASTROS = "http://api.open-notify.org/astros.json"
COINGECKO = "https://api.coingecko.com/api/v3/simple/price"

# (lat min, lat max, lon min, lon max, name), checked in order; oceans are the fallback.
REGIONS = [
    (12, 42, 25, 63, "the Middle East"),
    (36, 71, -25, 45, "Europe"),
    (-35, 37, -18, 52, "Africa"),
    (5, 78, 45, 180, "Asia"),
    (-11, 20, 95, 141, "South East Asia"),
    (-47, -10, 112, 179, "Australia and New Zealand"),
    (7, 83, -168, -52, "North America"),
    (-56, 13, -82, -34, "South America"),
]


def _fail(what: str) -> ValueError:
    return ValueError(f"The {what} service isn't answering right now. Try again in a bit.")


async def fetch(http: httpx.AsyncClient, url: str, what: str, params: dict | None = None,
                missing: str | None = None) -> httpx.Response:
    """GET with a short timeout; HTTP trouble becomes a friendly ValueError."""
    try:
        r = await http.get(url, params=params, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
    except httpx.HTTPError:
        raise _fail(what) from None
    if r.status_code == 404 and missing:
        raise ValueError(missing)
    if r.status_code >= 400:
        raise _fail(what)
    return r


async def fetch_json(http: httpx.AsyncClient, url: str, what: str, params: dict | None = None,
                     missing: str | None = None):
    r = await fetch(http, url, what, params, missing)
    try:
        return r.json()
    except ValueError:
        raise _fail(what) from None


def _clip(text: str, limit: int = 200) -> str:
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def _count(value, default: int, top: int) -> int:
    try:
        return min(max(int(value), 1), top)
    except (TypeError, ValueError):
        return default


def parse_rss(text: str) -> list[tuple[str, str]]:
    """(title, description) of each RSS item. Refuses DTDs and entities (no defusedxml here)."""
    if len(text) > MAX_XML or re.search(r"<!\s*(DOCTYPE|ENTITY)", text, re.I):
        raise ValueError("That news feed looked unsafe, so I didn't read it.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise ValueError("That news feed came back garbled.") from None
    return [((item.findtext("title") or "").strip(), (item.findtext("description") or "").strip())
            for item in root.iter("item") if (item.findtext("title") or "").strip()]


async def headlines(http: httpx.AsyncClient, section: str, count: int) -> str:
    section = section if section in SECTIONS else "top"
    r = await fetch(http, BBC + SECTIONS[section], "BBC News")
    items = parse_rss(r.text)[:count]
    if not items:
        return f"The BBC {section} feed is empty right now."
    label = "top stories" if section == "top" else f"{section} headlines"
    return f"BBC {label}:\n" + "\n".join(
        f"- {title}" + (f": {_clip(desc)}" if desc else "") for title, desc in items)


async def hacker_news(http: httpx.AsyncClient, count: int) -> str:
    ids = await fetch_json(http, f"{HN}/topstories.json", "Hacker News")
    ids = [i for i in (ids or []) if isinstance(i, int)][:count]
    items = await asyncio.gather(*(fetch_json(http, f"{HN}/item/{i}.json", "Hacker News") for i in ids))
    lines = []
    for item in items:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        site = urlparse(item.get("url") or "").netloc.removeprefix("www.")
        lines.append(f"- {item['title']}" + (f" ({site})" if site else "")
                     + f", {item.get('score', 0)} points, {item.get('descendants', 0)} comments")
    return "Top Hacker News stories:\n" + "\n".join(lines) if lines else "Hacker News has nothing to show right now."


async def earthquakes(http: httpx.AsyncClient, period: str) -> str:
    period = "week" if period == "week" else "day"
    span = "past week" if period == "week" else "past day"
    quakes = (await fetch_json(http, f"{USGS}/significant_{period}.geojson", "USGS earthquake")).get("features") or []
    heading = f"Significant earthquakes in the {span}"
    if not quakes:
        quakes = (await fetch_json(http, f"{USGS}/4.5_{period}.geojson", "USGS earthquake")).get("features") or []
        if not quakes:
            return f"No significant earthquakes in the {span}, and none of magnitude 4.5 or more."
        heading = f"No significant earthquakes in the {span}. The strongest of magnitude 4.5 or more"
    quakes = sorted(quakes, key=lambda q: -(q.get("properties", {}).get("mag") or 0))[:5]
    lines = []
    for q in quakes:
        p = q.get("properties", {})
        when = datetime.fromtimestamp((p.get("time") or 0) / 1000, timezone.utc).strftime("%a %d %b %H:%M UTC")
        lines.append(f"- Magnitude {p.get('mag')}, {p.get('place') or 'unknown place'}, {when}"
                     + (", tsunami warning issued" if p.get("tsunami") else ""))
    return f"{heading}:\n" + "\n".join(lines)


def region(lat: float, lon: float) -> str:
    if lat < -60:
        return "Antarctica and the Southern Ocean"
    if lat > 78:
        return "the Arctic"
    for lat0, lat1, lon0, lon1, name in REGIONS:
        if lat0 <= lat <= lat1 and lon0 <= lon <= lon1:
            return name
    if -70 <= lon <= 20:
        return "the Atlantic Ocean"
    if 20 < lon <= 120 and lat < 30:
        return "the Indian Ocean"
    return "the Pacific Ocean"


async def iss(http: httpx.AsyncClient) -> str:
    body = await fetch_json(http, ISS_NOW, "space station tracker")
    try:
        lat = float(body["iss_position"]["latitude"])
        lon = float(body["iss_position"]["longitude"])
    except (KeyError, TypeError, ValueError):
        raise _fail("space station tracker") from None
    ns, ew = ("north" if lat >= 0 else "south"), ("east" if lon >= 0 else "west")
    return (f"The International Space Station is roughly over {region(lat, lon)}, at "
            f"{abs(lat):.1f} degrees {ns}, {abs(lon):.1f} degrees {ew}.")


async def astronauts(http: httpx.AsyncClient) -> str:
    body = await fetch_json(http, ASTROS, "people-in-space")
    people = body.get("people") or []
    if not people:
        return "The people-in-space list is empty right now."
    crafts: dict[str, list[str]] = {}
    for p in people:
        crafts.setdefault(p.get("craft") or "unknown craft", []).append(p.get("name") or "someone")
    return f"{len(people)} people are in space right now. " + " ".join(
        f"On the {craft}: {', '.join(names)}." for craft, names in crafts.items())


def _summary(body: dict) -> str:
    extract = _clip(body.get("extract") or "", 700)
    if body.get("type") == "disambiguation":
        return f"'{body.get('title')}' could mean several things on Wikipedia. Ask about a more specific topic."
    return f"{body.get('title')}: {extract or 'Wikipedia has no summary for it.'}"


async def wikipedia(http: httpx.AsyncClient, topic: str) -> str:
    topic = re.sub(r"\s+", " ", topic or "").strip()[:200]
    if not topic:
        raise ValueError("Say which topic to look up.")
    title = quote(topic.replace(" ", "_"), safe="")
    body = await fetch_json(http, f"{WIKI}/page/summary/{title}", "Wikipedia",
                            missing=f"Wikipedia has no page called {topic}.")
    return _summary(body)


async def random_article(http: httpx.AsyncClient) -> str:
    return "A random Wikipedia article. " + _summary(await fetch_json(http, f"{WIKI}/page/random/summary", "Wikipedia"))


async def on_this_day(http: httpx.AsyncClient, count: int, today: date | None = None) -> str:
    today = today or date.today()
    body = await fetch_json(http, f"{WIKI}/feed/onthisday/events/{today:%m}/{today:%d}", "Wikipedia")
    events = sorted((e for e in body.get("events") or [] if e.get("text") and e.get("year") is not None),
                    key=lambda e: e["year"])
    if not events:
        return "Wikipedia has no events for today."
    if len(events) > count:  # spread the picks across the centuries
        step = (len(events) - 1) / (count - 1) if count > 1 else 0
        events = [events[round(i * step)] for i in range(count)]
    return f"On this day, {today.day} {today:%B}:\n" + "\n".join(
        f"- {e['year']}: {_clip(e['text'], 250)}" for e in events)


async def crypto(http: httpx.AsyncClient, coins: list[str] | None, currency: str) -> str:
    coins = [c.strip().lower().replace(" ", "-") for c in (coins or []) if isinstance(c, str) and c.strip()]
    coins = [c for c in coins if re.fullmatch(r"[a-z0-9-]{1,40}", c)][:10] or ["bitcoin", "ethereum"]
    cur = currency.lower() if re.fullmatch(r"[A-Za-z]{3}", currency or "") else "gbp"
    body = await fetch_json(http, COINGECKO, "CoinGecko price", params={
        "ids": ",".join(coins), "vs_currencies": cur, "include_24hr_change": "true"})
    lines = []
    for coin in coins:
        price = (body.get(coin) or {}).get(cur)
        if price is None:
            lines.append(f"- {coin}: CoinGecko doesn't know that coin.")
            continue
        change = body[coin].get(f"{cur}_24h_change")
        move = "" if change is None else f", {'up' if change >= 0 else 'down'} {abs(change):.1f}% in 24 hours"
        lines.append(f"- {coin.replace('-', ' ').title()}: {price:,.2f} {cur.upper()}{move}")
    return "Crypto prices from CoinGecko:\n" + "\n".join(lines)


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "news_headlines",
            "description": "Latest headlines. kind 'bbc' gives BBC News titles with a line each for a section; "
                           "'hacker_news' gives the top Hacker News tech stories.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["bbc", "hacker_news"]},
                    "section": {"type": "string", "enum": list(SECTIONS), "description": "BBC section. Default top."},
                    "count": {"type": "integer", "description": "How many, 1 to 10. Default 5."},
                },
                "required": ["kind"],
                "additionalProperties": False,
            },
        },
        {
            "name": "world_info",
            "description": "Live facts from public feeds. kind: 'earthquakes' (significant quakes, period day or "
                           "week), 'iss' (where the space station is now), 'astronauts' (who is in space), "
                           "'wikipedia' (short summary of topic), 'on_this_day' (history events today), "
                           "'random_article' (something random from Wikipedia), 'crypto' (prices of coins, "
                           "CoinGecko ids like bitcoin, ethereum, solana, dogecoin).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["earthquakes", "iss", "astronauts", "wikipedia",
                                                        "on_this_day", "random_article", "crypto"]},
                    "period": {"type": "string", "enum": ["day", "week"]},
                    "topic": {"type": "string", "description": "Wikipedia topic, e.g. 'Isaac Newton'."},
                    "coins": {"type": "array", "items": {"type": "string"}},
                    "count": {"type": "integer", "description": "On-this-day events, 3 to 5. Default 4."},
                },
                "required": ["kind"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {"news_headlines", "world_info"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient) -> str:
    kind = args.get("kind")
    if name == "news_headlines":
        count = _count(args.get("count"), 5, 10)
        if kind == "hacker_news":
            return await hacker_news(http, count)
        return await headlines(http, args.get("section") or "top", count)
    if kind == "earthquakes":
        return await earthquakes(http, args.get("period") or "day")
    if kind == "iss":
        return await iss(http)
    if kind == "astronauts":
        return await astronauts(http)
    if kind == "wikipedia":
        return await wikipedia(http, args.get("topic") or "")
    if kind == "on_this_day":
        return await on_this_day(http, min(max(_count(args.get("count"), 4, 5), 3), 5))
    if kind == "random_article":
        return await random_article(http)
    if kind == "crypto":
        return await crypto(http, args.get("coins"), settings.currency)
    raise ValueError("Pick earthquakes, iss, astronauts, wikipedia, on_this_day, random_article or crypto.")
