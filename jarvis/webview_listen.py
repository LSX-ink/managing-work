"""Internet radio and podcasts in a pop-up player on the Alfred screen.

Stations come from radio-browser.info and podcasts from the iTunes search; both are keyless and only get the
search words. Only https streams and episodes are offered, so the page never loads plain http audio.
"""

import httpx

import screen
import webview_common as web
from config import Settings

screen.EXTRA_KINDS.update({"radio", "gallery"})

RADIO = "https://de1.api.radio-browser.info/json/stations/search"
MAX_EPISODES = 15
ACTIONS = ["radio_search", "radio_play", "podcast_search", "podcast_episodes"]


async def stations(http: httpx.AsyncClient, query: str) -> list[dict]:
    query = web.need(query, "station", 80)
    found = await web.get_json(http, RADIO, "radio station directory", {
        "name": query, "limit": 10, "hidebroken": "true", "order": "clickcount", "reverse": "true"})
    out = []
    for s in found if isinstance(found, list) else []:
        src = web.https(s.get("url_resolved") or s.get("url"))
        if not src or not web.clean(s.get("name")):
            continue
        bits = [web.clean(s.get("country"), 40), web.clean(s.get("tags"), 60).replace(",", ", ")]
        if s.get("bitrate"):
            bits.append(f"{int(s['bitrate'])} kbps")
        out.append({"title": web.clean(s.get("name"), 100), "subtitle": " · ".join(b for b in bits if b),
                    "src": src, "image": web.https(s.get("favicon"))})
    if not out:
        raise ValueError(f"I couldn't find a radio station called {query} with a secure stream.")
    return out


async def radio(http: httpx.AsyncClient, query: str, play: bool) -> screen.Shown:
    found = await stations(http, query)
    card = screen.card("radio", "Radio", "webview-radio", data={"tracks": found, "live": True,
                                                                 "autoplay": 0 if play else -1},
                       text="" if play else "Tap a station to play it.")
    if play:
        return screen.Shown(f"Playing {found[0]['title']} on the screen.", card)
    return screen.Shown(f"I found {len(found)} stations; they're on the screen. The top one is {found[0]['title']}.", card)


async def _itunes(http: httpx.AsyncClient, query: str) -> list[dict]:
    query = web.need(query, "podcast", 100)
    body = await web.get_json(http, web.ITUNES, "podcast search", {"media": "podcast", "term": query, "limit": 12})
    shows = [r for r in (body.get("results") or []) if web.https(r.get("feedUrl"))]
    if not shows:
        raise ValueError(f"I couldn't find a podcast called {query}.")
    return shows


async def podcast_search(http: httpx.AsyncClient, query: str) -> screen.Shown:
    shows = await _itunes(http, query)
    tiles = [{"title": web.clean(s.get("collectionName"), 120), "subtitle": web.clean(s.get("artistName"), 80),
              "image": web.https(s.get("artworkUrl600") or s.get("artworkUrl100")),
              "say": f"Show the latest episodes of the podcast feed {s['feedUrl']}"} for s in shows]
    card = screen.card("gallery", f"Podcasts: {web.clean(query, 40)}", "webview-podcasts", data={"tiles": tiles},
                       text="Tap a podcast to see its latest episodes.")
    return screen.Shown(f"I found {len(tiles)} podcasts; the top one is {tiles[0]['title']}. They're on the screen.", card)


async def podcast_episodes(http: httpx.AsyncClient, feed_url: str, query: str) -> screen.Shown:
    if not feed_url:
        feed_url = (await _itunes(http, query))[0]["feedUrl"]
    r = await web.get_public(http, feed_url, "podcast feed", web.MAX_FEED)
    info, items = web.parse_feed(r.text)
    tracks = [{"title": i["title"], "subtitle": i["date"][:16], "src": i["audio"], "image": info["image"]}
              for i in items if i["audio"]][:MAX_EPISODES]
    if not tracks:
        raise ValueError("That podcast has no episodes I can play here.")
    title = info["title"] or "Podcast"
    card = screen.card("radio", title, "webview-podcast", data={"tracks": tracks, "live": False, "autoplay": -1,
                                                                "image": info["image"]},
                       text="Tap an episode to play it.")
    return screen.Shown(f"The latest episodes of {title} are on the screen; the newest is {tracks[0]['title']}.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "radio_and_podcasts",
        "description": "Listen to internet radio and podcasts in a pop-up player on the Alfred screen. "
                       "radio_search: find stations by name (e.g. 'BBC Radio 6', 'jazz', 'Capital'); radio_play: "
                       "play the best match straight away; podcast_search: find podcasts with cover art; "
                       "podcast_episodes: the latest episodes of a podcast (feed_url from podcast_search, or query "
                       "with its name) to tap and play.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "query": {"type": "string", "description": "Station or podcast name or topic."},
                "feed_url": {"type": "string", "description": "podcast_episodes: the podcast's RSS feed link."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"radio_and_podcasts"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    action, query = args.get("action"), args.get("query") or ""
    if action in ("radio_search", "radio_play"):
        return await radio(http, query, action == "radio_play")
    if action == "podcast_search":
        return await podcast_search(http, query)
    if action == "podcast_episodes":
        return await podcast_episodes(http, (args.get("feed_url") or "").strip(), query)
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
