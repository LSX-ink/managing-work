"""Places on the Alfred screen: an OpenStreetMap map of a place, the distance as the crow flies between two places,
country facts with the flag, and a rain radar picture around a place.

Place names go to Open-Meteo's geocoder, country names to REST Countries, and the radar comes from RainViewer;
all keyless. The map window embeds only openstreetmap.org's own embed page, sandboxed.
"""

import math
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

import screen
import webview_common as web
from config import Settings

screen.EXTRA_KINDS.update({"map", "webcard"})

OSM_EMBED = "https://www.openstreetmap.org/export/embed.html"
OSM_TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
COUNTRIES = "https://restcountries.com/v3.1/name/"
COUNTRY_FIELDS = "name,capital,population,region,subregion,languages,currencies,flags,area,latlng"
RAINVIEWER = "https://api.rainviewer.com/public/weather-maps.json"
RADAR_ZOOM = 6
ACTIONS = ["map", "distance", "country", "radar"]


def _span(kind: str) -> float:
    """Half the map height in degrees, from the geocoder's feature code (country, region, city, town)."""
    if kind.startswith("PCL"):
        return 6
    return {"ADM1": 2, "ADM2": 0.7, "PPLC": 0.15, "PPLA": 0.12}.get(kind, 0.06)


def embed_url(south: float, west: float, north: float, east: float, marker: dict) -> str:
    south, north = max(south, -85.0), min(north, 85.0)
    return (f"{OSM_EMBED}?bbox={west:.4f}%2C{south:.4f}%2C{east:.4f}%2C{north:.4f}&layer=mapnik"
            f"&marker={marker['lat']:.5f}%2C{marker['lon']:.5f}")


def _point(p: dict) -> dict:
    return {"label": p["label"], "lat": round(p["lat"], 5), "lon": round(p["lon"], 5)}


def _coords(p: dict) -> str:
    return f"{abs(p['lat']):.4f}°{'N' if p['lat'] >= 0 else 'S'}, {abs(p['lon']):.4f}°{'E' if p['lon'] >= 0 else 'W'}"


def _osm_link(p: dict) -> str:
    return f"https://www.openstreetmap.org/?mlat={p['lat']:.5f}&mlon={p['lon']:.5f}"


async def show_map(http: httpx.AsyncClient, place: str) -> screen.Shown:
    p = await web.geocode(http, place)
    s = _span(p["kind"])
    wide = s * 1.6 / max(0.3, math.cos(math.radians(p["lat"])))
    src = embed_url(p["lat"] - s, p["lon"] - wide, p["lat"] + s, p["lon"] + wide, p)
    card = screen.card("map", p["label"], f"webview-map-{p['label']}", data={
        "embed": src, "places": [_point(p)], "link": _osm_link(p)},
        text=f"{p['label']} · {_coords(p)}",
        buttons=[{"label": "Weather here", "say": f"What's the weather in {p['name']}?"},
                 {"label": "Rain radar", "say": f"Show me the rain radar for {p['name']}."}])
    return screen.Shown(f"{p['label']} is on the map on the screen.", card)


async def distance(http: httpx.AsyncClient, place: str, other: str) -> screen.Shown:
    a, b = await web.geocode(http, place), await web.geocode(http, other)
    km = web.haversine_km(a, b)
    miles = km / 1.609344
    pad_lat = max(abs(a["lat"] - b["lat"]) * 0.2, 0.05)
    pad_lon = max(abs(a["lon"] - b["lon"]) * 0.2, 0.08)
    src = embed_url(min(a["lat"], b["lat"]) - pad_lat, min(a["lon"], b["lon"]) - pad_lon,
                    max(a["lat"], b["lat"]) + pad_lat, max(a["lon"], b["lon"]) + pad_lon, a)
    said = f"{a['name']} to {b['name']} is {miles:,.0f} miles ({km:,.0f} km) as the crow flies."
    card = screen.card("map", f"{a['name']} to {b['name']}", "webview-distance", data={
        "embed": src, "places": [_point(a), _point(b)], "distance": f"{miles:,.0f} miles · {km:,.0f} km",
        "link": _osm_link(a)},
        text=f"{said}\nA: {a['label']} ({_coords(a)})\nB: {b['label']} ({_coords(b)})\nThe pin marks A.")
    return screen.Shown(said, card)


def _pick_country(found: list, name: str) -> dict:
    want = name.lower()
    for c in found:
        names = c.get("name") or {}
        if want in (str(names.get("common", "")).lower(), str(names.get("official", "")).lower()):
            return c
    return max(found, key=lambda c: c.get("population") or 0)


async def country(http: httpx.AsyncClient, name: str) -> screen.Shown:
    name = web.need(name, "country", 80)
    found = await web.get_json(http, COUNTRIES + quote(name, safe=""), "REST Countries", {"fields": COUNTRY_FIELDS},
                               missing=f"I don't know a country called {name}.")
    if not isinstance(found, list) or not found:
        raise ValueError(f"I don't know a country called {name}.")
    c = _pick_country(found, name)
    common = web.clean((c.get("name") or {}).get("common"), 80) or name
    official = web.clean((c.get("name") or {}).get("official"), 120)
    capital = ", ".join(web.clean(x, 60) for x in (c.get("capital") or [])[:3])
    languages = ", ".join(web.clean(x, 40) for x in list((c.get("languages") or {}).values())[:5])
    currencies = ", ".join(f"{web.clean(v.get('name'), 40)} ({web.clean(v.get('symbol'), 5)})".replace(" ()", "")
                           for v in list((c.get("currencies") or {}).values())[:3] if isinstance(v, dict))
    region = " · ".join(x for x in (web.clean(c.get("region"), 40), web.clean(c.get("subregion"), 60)) if x)
    facts = [["Capital", capital], ["Population", f"{int(c.get('population') or 0):,}"],
             ["Area", f"{float(c.get('area') or 0):,.0f} km²"], ["Region", region],
             ["Languages", languages], ["Currency", currencies]]
    facts = [f for f in facts if f[1] and f[1] not in ("0", "0 km²")]
    flag = web.https((c.get("flags") or {}).get("png") or (c.get("flags") or {}).get("svg"))
    card = screen.card("webcard", common, f"webview-country-{common}", data={
        "heading": official or common, "site": "REST Countries", "image": flag,
        "text": web.clean((c.get("flags") or {}).get("alt"), 400), "facts": facts},
        buttons=[{"label": "Show on a map", "say": f"Show {common} on a map on screen."},
                 {"label": "Tell me more", "say": f"Show me the Wikipedia article about {common} on screen."}])
    return screen.Shown(f"{common}: " + "; ".join(f"{k.lower()} {v}" for k, v in facts[:3]) + ".", card)


def tile_xy(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    n = 2 ** zoom
    lat = max(min(lat, 85.0), -85.0)
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


async def radar(http: httpx.AsyncClient, place: str) -> screen.Shown:
    p = await web.geocode(http, place)
    maps = await web.get_json(http, RAINVIEWER, "RainViewer radar")
    frames = ((maps.get("radar") or {}).get("past") or []) if isinstance(maps, dict) else []
    host = web.https(maps.get("host")) if isinstance(maps, dict) else ""
    if not frames or not host or not str(frames[-1].get("path", "")).startswith("/"):
        raise ValueError("The rain radar isn't available right now.")
    frame = frames[-1]
    z, n = RADAR_ZOOM, 2 ** RADAR_ZOOM
    x, y = tile_xy(p["lat"], p["lon"], z)
    cx, cy = int(x), min(max(int(y), 1), n - 2)
    tiles = [{"base": OSM_TILE.format(z=z, x=tx % n, y=ty),
              "overlay": f"{host}{frame['path']}/256/{z}/{tx % n}/{ty}/2/1_1.png"}
             for ty in (cy - 1, cy, cy + 1) for tx in (cx - 1, cx, cx + 1)]
    when = datetime.fromtimestamp(int(frame.get("time") or 0), timezone.utc).astimezone().strftime("%H:%M")
    card = screen.card("map", f"Rain radar: {p['name']}", "webview-radar", data={
        "mode": "radar", "tiles": tiles, "marker": {"x": round((x - cx + 1) / 3, 4), "y": round((y - cy + 1) / 3, 4)},
        "credit": "Radar: RainViewer · Map: © OpenStreetMap contributors"},
        text=f"Rain radar around {p['label']} at {when}.",
        buttons=[{"label": "Refresh", "say": f"Show me the rain radar for {p['name']}."}])
    return screen.Shown(f"The rain radar around {p['name']} from {when} is on the screen.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "maps_and_places",
        "description": "Maps and places in a pop-up on the Alfred screen. map: show a place, town, address or "
                       "country on an OpenStreetMap map; distance: how far place is from other_place as the crow "
                       "flies (miles and km); country: facts and flag of a country (capital, population, "
                       "languages, currency); radar: the latest rain radar picture around a place (default home city).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "place": {"type": "string", "description": "Place or country name, e.g. 'Brighton'."},
                "other_place": {"type": "string", "description": "distance: the second place."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"maps_and_places"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    action, place = args.get("action"), args.get("place") or ""
    if action == "map":
        return await show_map(http, place or settings.city)
    if action == "distance":
        return await distance(http, place or settings.city, args.get("other_place") or "")
    if action == "country":
        return await country(http, place)
    if action == "radar":
        return await radar(http, place or settings.city)
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
