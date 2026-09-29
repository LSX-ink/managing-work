"""TV shows: which episode you are on, what is next up, and TVmaze lookups (search, episodes, next airing, cast).

TVmaze (https://api.tvmaze.com) needs no key and is read-only. Only the show name you say is ever sent.
Progress is kept on the show's entry in watchlist.json (season and episode you last watched).
"""

from datetime import date

import httpx

import feeds
import homestore as hs
import screen
import watchlist_store as ws
from config import Settings

TVMAZE = "https://api.tvmaze.com"
ACTIONS = ["show_progress", "episode_done", "show_status", "tv_search", "tv_add", "tv_episodes", "tv_next_episode", "tv_cast"]


def _show_item(data: dict, title, create: bool = False) -> dict:
    title = hs.need(title, "show", 120)
    shows = [i for i in data["items"] if isinstance(i, dict) and i["kind"] == "show"]
    key = hs.find([i["title"] for i in shows], title)
    item = next((i for i in shows if i["title"] == key), None) if key else None
    if item is None and create:
        item = {"title": title, "kind": "show", "status": "to watch", "genre": "", "minutes": 0, "moods": [], "kids_safe": False,
                "year": "", "image": "", "added": hs.today().isoformat(), "rating": None, "review": "", "watched": "",
                "rewatch": False, "season": 0, "episode": 0}
        ws.add_capped(data["items"], item, "watchlist")
    if item is None:
        raise ValueError(f"{title} isn't in your watchlist as a show. Add it first.")
    return item


def _number(value, what: str, low: int = 0) -> int:
    return int(hs.number(value, what, low, 500))


def _on(item: dict) -> str:
    return f"season {item.get('season', 0)}, episode {item.get('episode', 0)}" if item.get("season") else "not started"


def show_progress(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    item = _show_item(data, args.get("title"), create=True)
    season, episode = _number(args.get("season"), "season", 1), _number(args.get("episode"), "episode", 0)
    item.update(season=season, episode=episode)
    ws.save(settings, data)
    return _status(settings, f"{item['title']}: you're on season {season}, episode {episode}. Next up is episode {episode + 1}.")


def episode_done(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    item = _show_item(data, args.get("title"))
    season, episode = item.get("season") or 1, (item.get("episode") or 0) + 1
    size = (item.get("seasons") or {}).get(str(season))
    if size and episode > size and str(season + 1) in (item.get("seasons") or {}):
        season, episode = season + 1, 1
    item.update(season=season, episode=episode, status="to watch")
    ws.save(settings, data)
    return _status(settings, f"Done, {item['title']} season {season}, episode {episode}. Next up is episode {episode + 1}.")


def _status(settings: Settings, said: str = "") -> screen.Shown | str:
    shows = [i for i in ws.load(settings)["items"] if isinstance(i, dict) and i["kind"] == "show" and i.get("season")
             and i.get("status") == "to watch"]
    if not shows:
        return "You're not following any shows yet. Say 'I'm on season 1 episode 3 of Slow Horses'."
    rows = [[i["title"], f"S{i['season']} E{i['episode']}", f"S{i['season']} E{i['episode'] + 1}"] for i in shows]
    tiles = [ws.tile(i["title"], f"Next: S{i['season']} E{i['episode'] + 1}", f"S{i['season']}E{i['episode']}", image=i.get("image", ""),
                     say=f"I watched the next episode of {i['title']}.") for i in shows]
    said = said or f"You're following {hs.plural(len(shows), 'show')}. Next up: " + "; ".join(
        f"{r[0]} {r[2]}" for r in rows[:4]) + "."
    return ws.board(said, "TV next up", "watchlist-shows", [ws.gallery(tiles, "Tap when you've watched the next one"),
                                                             ws.table(["Show", "Watched up to", "Next up"], rows)])


def show_status(settings: Settings) -> screen.Shown | str:
    return _status(settings)


async def _get(http: httpx.AsyncClient, path: str, what: str, params=None, missing=None):
    return await feeds.fetch_json(http, TVMAZE + path, what, params, missing)


async def _show(http: httpx.AsyncClient, settings: Settings, title, embed: str = "") -> dict:
    """The TVmaze show for a name: the saved id if the show is on the watchlist, else the best match by name."""
    title = hs.need(title, "show", 120)
    params = {"embed": embed} if embed else None
    saved = next((i for i in ws.load(settings)["items"] if isinstance(i, dict) and i["kind"] == "show"
                  and i.get("tvmaze_id") and i["title"].lower() == title.lower()), None)
    if saved:
        found = await _get(http, f"/shows/{int(saved['tvmaze_id'])}", "TVmaze", params)
    else:
        found = await _get(http, "/singlesearch/shows", "TVmaze", {"q": title, **(params or {})},
                           missing=f"TVmaze doesn't know a show called {title}.")
    if not isinstance(found, dict) or not found.get("id"):
        raise ValueError(f"TVmaze doesn't know a show called {title}.")
    return found


async def tv_search(http: httpx.AsyncClient, query) -> screen.Shown:
    query = hs.need(query, "show to search for", 100)
    found = await _get(http, "/search/shows", "TVmaze", {"q": query})
    tiles = []
    for entry in (found if isinstance(found, list) else [])[:12]:
        show = entry.get("show") or {}
        if not show.get("name") or not show.get("id"):
            continue
        year = (show.get("premiered") or "")[:4]
        genres = ", ".join((show.get("genres") or [])[:2])
        tiles.append(ws.tile(show["name"], " · ".join(x for x in (year, genres, show.get("status") or "") if x),
                             image=(show.get("image") or {}).get("medium", ""),
                             say=f"Add the TV show {show['name']} (TVmaze id {int(show['id'])}) to my watchlist."))
    if not tiles:
        raise ValueError(f"TVmaze found no shows for {query}.")
    return ws.board(f"I found {len(tiles)} shows for {query}; the top one is {tiles[0]['title']}. Tap one to add it.",
                    f"TV search: {query}", "watchlist-tvsearch", [ws.gallery(tiles)])


async def tv_add(http: httpx.AsyncClient, settings: Settings, args: dict) -> str:
    try:
        tv_id = int(args.get("tvmaze_id"))
    except (TypeError, ValueError):
        show = await _show(http, settings, args.get("title"))
    else:
        show = await _get(http, f"/shows/{tv_id}", "TVmaze", missing="TVmaze doesn't know that show.")
    if not isinstance(show, dict) or not show.get("name"):
        raise ValueError("TVmaze sent nothing I can use for that show.")
    data = ws.load(settings)
    if any(i.get("tvmaze_id") == show["id"] for i in data["items"] if isinstance(i, dict)):
        return f"{show['name']} is already on your watchlist."
    item = {"title": hs.clean(show["name"], 120), "kind": "show", "status": "to watch",
            "genre": ", ".join((show.get("genres") or [])[:2]).lower(), "minutes": int(show.get("runtime") or 0),
            "moods": [], "kids_safe": False, "year": (show.get("premiered") or "")[:4],
            "image": ws.https((show.get("image") or {}).get("medium")), "added": hs.today().isoformat(), "rating": None,
            "review": "", "watched": "", "rewatch": False, "season": 0, "episode": 0, "tvmaze_id": int(show["id"])}
    ws.add_capped(data["items"], item, "watchlist")
    ws.save(settings, data)
    return f"Added {item['title']} to your watchlist with its TVmaze details."


def _day(value: str) -> str:
    try:
        return hs.spoken(date.fromisoformat(value))
    except ValueError:
        return value or "date to be confirmed"


async def tv_episodes(http: httpx.AsyncClient, settings: Settings, args: dict) -> screen.Shown:
    show = await _show(http, settings, args.get("title"))
    episodes = await _get(http, f"/shows/{int(show['id'])}/episodes", "TVmaze")
    episodes = [e for e in (episodes if isinstance(episodes, list) else []) if isinstance(e, dict)]
    if not episodes:
        raise ValueError(f"TVmaze has no episodes listed for {show['name']} yet.")
    sizes: dict[str, int] = {}
    for e in episodes:
        sizes[str(e.get("season"))] = sizes.get(str(e.get("season")), 0) + 1
    data = ws.load(settings)
    saved = next((i for i in data["items"] if isinstance(i, dict) and i["kind"] == "show" and i.get("tvmaze_id") == show["id"]), None)
    if saved is not None:
        saved["seasons"] = sizes
        ws.save(settings, data)
    season = str(args.get("season") or (saved or {}).get("season") or max(int(s) for s in sizes))
    rows = [[f"E{e.get('number')}", hs.clean(e.get("name"), 80), _day(e.get("airdate") or ""), f"{e['runtime']} min" if e.get("runtime") else ""]
            for e in episodes if str(e.get("season")) == season]
    if not rows:
        raise ValueError(f"{show['name']} has no season {season} on TVmaze.")
    return ws.board(f"{show['name']} season {season} has {hs.plural(len(rows), 'episode')}; {hs.plural(len(sizes), 'season')} in all.",
                    f"{show['name']}: season {season}", "watchlist-episodes", [ws.table(["Ep", "Title", "Aired", "Length"], rows)])


async def tv_next_episode(http: httpx.AsyncClient, settings: Settings, title) -> screen.Shown | str:
    show = await _show(http, settings, title, embed="nextepisode")
    nxt = (show.get("_embedded") or {}).get("nextepisode")
    if not isinstance(nxt, dict):
        state = "has ended" if show.get("status") == "Ended" else "has no new episode announced yet"
        return f"{show['name']} {state}."
    when = _day(nxt.get("airdate") or "")
    time = f" at {nxt['airtime']}" if nxt.get("airtime") else ""
    text = f"The next episode of {show['name']} is season {nxt.get('season')}, episode {nxt.get('number')}, {hs.clean(nxt.get('name'), 80)}, on {when}{time}."
    facts = [["Show", show["name"]], ["Episode", f"S{nxt.get('season')} E{nxt.get('number')}: {hs.clean(nxt.get('name'), 80)}"],
             ["Airs", when + time], ["Network", hs.clean(((show.get("network") or show.get("webChannel")) or {}).get("name"), 60)]]
    return ws.board(text, f"Next: {show['name']}", "watchlist-next", [ws.table([], facts)])


async def tv_cast(http: httpx.AsyncClient, settings: Settings, title) -> screen.Shown:
    show = await _show(http, settings, title)
    cast = await _get(http, f"/shows/{int(show['id'])}/cast", "TVmaze")
    rows = [[hs.clean((c.get("person") or {}).get("name"), 60), hs.clean((c.get("character") or {}).get("name"), 60)]
            for c in (cast if isinstance(cast, list) else []) if isinstance(c, dict)][:20]
    if not rows:
        raise ValueError(f"TVmaze has no cast listed for {show['name']}.")
    return ws.board(f"The cast of {show['name']} includes " + ", ".join(r[0] for r in rows[:4]) + ".", f"Cast: {show['name']}",
                    "watchlist-cast", [ws.table(["Actor", "Plays"], rows)])


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "watch_shows",
        "description": "TV show tracker and TVmaze lookups. show_progress (title, season, episode = last one watched), "
                       "episode_done (title; moves on one episode), show_status (which episode am I on, what's next up). "
                       "tv_search (query) finds shows to add; tv_add (title or tvmaze_id); tv_episodes (title, season); "
                       "tv_next_episode (title) answers 'when is the next episode of X'; tv_cast (title).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "title": text, "query": text, "season": {"type": "integer", "minimum": 1},
                "episode": {"type": "integer", "minimum": 0}, "tvmaze_id": {"type": "integer"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"watch_shows"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    a = args.get("action")
    if a == "show_progress":
        return show_progress(settings, args)
    if a == "episode_done":
        return episode_done(settings, args)
    if a == "show_status":
        return show_status(settings)
    if a == "tv_search":
        return await tv_search(http, args.get("query") or args.get("title"))
    if a == "tv_add":
        return await tv_add(http, settings, args)
    if a == "tv_episodes":
        return await tv_episodes(http, settings, args)
    if a == "tv_next_episode":
        return await tv_next_episode(http, settings, args.get("title"))
    if a == "tv_cast":
        return await tv_cast(http, settings, args.get("title"))
    raise ValueError("Unknown show action.")
