"""Play the latest radio news bulletin, read by the station's own presenters.

"Play today's news" finds the newest episode of a station's news bulletin podcast (through the keyless iTunes
search, which only gets the bulletin's name) and plays it in the radio pop-up once Alfred has finished speaking.
By default it stops after the opening headlines (the first three main stories); pressing Play carries on with the
rest. The top three BBC headlines are shown as text too, for anyone who can't hear it.
"""

import httpx

import feeds
import screen
import webview_common as web
from config import Settings

# name: (spoken label, podcast to look for, publisher it must come from, seconds of opening headlines)
STATIONS = {
    "bbc": ("BBC World Service", "Global News Podcast", "BBC", 100),
    "bbc_minute": ("BBC Minute", "BBC Minute", "BBC", 0),
    "npr": ("NPR News", "NPR News Now", "NPR", 120),
}
ALIASES = {"world service": "bbc", "bbc world service": "bbc", "bbc news": "bbc", "radio 4": "bbc",
           "minute": "bbc_minute", "bbc minute": "bbc_minute", "npr news": "npr", "us": "npr", "american": "npr"}


def station_key(name: str) -> str:
    name = str(name or "bbc").strip().lower().replace("-", " ")
    return name.replace(" ", "_") if name.replace(" ", "_") in STATIONS else ALIASES.get(name, "bbc")


async def latest_episode(http: httpx.AsyncClient, key: str) -> tuple[dict, dict]:
    label, show, publisher, _ = STATIONS[key]
    body = await web.get_json(http, web.ITUNES, "news bulletin search", {"media": "podcast", "term": show, "limit": 10})
    shows = [r for r in (body.get("results") or []) if web.https(r.get("feedUrl"))
             and publisher.lower() in f"{r.get('artistName', '')} {r.get('collectionName', '')}".lower()]
    if not shows:
        raise ValueError(f"I couldn't find the {label} bulletin right now.")
    r = await web.get_public(http, shows[0]["feedUrl"], "news bulletin", web.MAX_FEED)
    info, items = web.parse_feed(r.text)
    episode = next((i for i in items if i["audio"]), None)
    if not episode:
        raise ValueError(f"The {label} bulletin has nothing I can play right now.")
    return info, episode


async def top_three(http: httpx.AsyncClient) -> list[str]:
    try:
        r = await feeds.fetch(http, feeds.BBC + feeds.SECTIONS["top"], "BBC News")
        return [title for title, _ in feeds.parse_rss(r.text)[:3]]
    except ValueError:
        return []  # the captions are a bonus; the bulletin still plays


async def play(http: httpx.AsyncClient, station: str, full: bool) -> screen.Shown:
    key = station_key(station)
    label, _, _, headline_secs = STATIONS[key]
    info, episode = await latest_episode(http, key)
    lines = await top_three(http)
    stop_after = 0 if full else headline_secs
    track = {"title": episode["title"], "subtitle": episode["date"][:22], "src": episode["audio"],
             "image": info["image"]}
    data = {"tracks": [track], "live": False, "autoplay": 0, "image": info["image"], "wait_speech": True,
            "stop_after": stop_after, "station": label, "headlines": lines}
    note = "Stops after the headlines; press Play for the full bulletin." if stop_after else ""
    card = screen.card("radio", f"News · {label}", "news-bulletin", data=data, text=note,
                       buttons=[{"label": "Full bulletin", "say": f"Play the full {label} news bulletin."}]
                       if stop_after else [])
    return screen.Shown(f"Here's the latest from {label}.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "news_bulletin",
        "description": "PLAY the latest radio news bulletin out loud in the news presenters' own voices (not Alfred's), "
                       "in a pop-up player. Use for 'play today's news', 'play the news', 'news bulletin', 'what's on "
                       "the radio news'. It plays the opening headlines (the main three stories) unless full is true. "
                       "Keep your own reply to one short line: the bulletin starts after you finish speaking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "station": {"type": "string", "enum": list(STATIONS),
                            "description": "bbc (BBC World Service, default), bbc_minute (a 60-second bulletin) "
                                           "or npr (NPR News, US)."},
                "full": {"type": "boolean", "description": "Play the whole bulletin, not just the headlines."},
            },
            "additionalProperties": False,
        },
    }]


NAMES = {"news_bulletin"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    return await play(http, args.get("station") or "bbc", bool(args.get("full")))
