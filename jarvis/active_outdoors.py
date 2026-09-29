"""Getting outdoors in the UK: is it good weather for a run, walk or ride (Open-Meteo forecast with the best hours
today), hiking kit checklists, the Countryside Code, hill-walking safety and saved walking routes with notes.

Only a city name goes to Open-Meteo, which is free and needs no key. Routes are saved under "routes" in active.json.
"""

import active_data as data
import active_store as store
import screen
from config import Settings
from feeds import fetch_json
from feeds_outdoors import FORECAST, UV_BANDS, place

NAMES = {"active_outdoors"}
ACTIONS = ["weather", "kit", "countryside_code", "hill_safety", "route_save", "route_list", "route_remove"]
ACTIVITIES = {"run": (6, 15), "running": (6, 15), "walk": (8, 20), "walking": (8, 20), "cycle": (10, 22),
              "cycling": (10, 22), "bike": (10, 22), "ride": (10, 22), "hike": (6, 18), "hiking": (6, 18)}
VERBS = {"run": "a run", "walk": "a walk", "cycle": "a bike ride", "hike": "a hike"}
CANON = {"running": "run", "walking": "walk", "cycling": "cycle", "bike": "cycle", "ride": "cycle", "hiking": "hike"}
HOURLY = "temperature_2m,precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m"
GOOD, OKAY = 75, 55


def score(temp: float, rain_chance: float, rain_mm: float, wind: float, gust: float, low: float, high: float) -> int:
    """0 to 100 for one hour: comfortable temperature, dry and not too windy."""
    points = (100 - max(0, low - temp) * 4 - max(0, temp - high) * 5 - rain_chance * 0.4 - rain_mm * 15
              - max(0, wind - 10) * 2.5 - max(0, gust - 30))
    return int(max(0, min(100, round(points))))


def _wind_word(mph: float) -> str:
    return "light wind" if mph < 10 else "a breeze" if mph < 18 else "windy" if mph < 28 else "very windy"


def _uv_note(uv) -> str:
    if uv is None:
        return ""
    for limit, word, advice in UV_BANDS:
        if uv < limit:
            return f" UV up to {uv:g} ({word})" + ("." if uv < 3 else f": {advice}.")
    return f" UV up to {uv:g} (extreme): cover up."


def _hours(forecast: dict) -> list[dict]:
    hourly, daily = forecast.get("hourly") or {}, forecast.get("daily") or {}
    times = hourly.get("time") or []
    if not times:
        raise ValueError("The forecast came back empty.")
    now = ((forecast.get("current") or {}).get("time") or times[0])[:13]
    first = int(((daily.get("sunrise") or [times[0]])[0])[11:13] or 0)
    last = int(((daily.get("sunset") or [times[-1]])[0])[11:13] or 23)
    out = []
    for i, t in enumerate(times):
        hour = int(t[11:13])
        if t[:13] < now or hour < first or hour >= last:
            continue

        def val(key, default=0.0, i=i):
            v = (hourly.get(key) or [])[i:i + 1]
            return default if not v or v[0] is None else float(v[0])
        out.append({"time": t[11:16], "temp": val("temperature_2m"), "pop": val("precipitation_probability"),
                    "mm": val("precipitation"), "wind": val("wind_speed_10m"), "gust": val("wind_gusts_10m")})
    return out


async def weather(http, settings: Settings, args: dict) -> str | screen.Shown:
    kind = CANON.get(store.clean(args.get("kind")).lower(), store.clean(args.get("kind")).lower() or "run")
    if kind not in VERBS:
        raise ValueError("Pick run, walk, cycle or hike.")
    low, high = ACTIVITIES[kind]
    p = await place(http, store.clean(args.get("city")) or settings.city.strip())
    forecast = await fetch_json(http, FORECAST, "forecast", params={
        "latitude": p["latitude"], "longitude": p["longitude"], "timezone": "auto", "forecast_days": 1,
        "hourly": HOURLY, "daily": "sunrise,sunset,uv_index_max", "current": "temperature_2m",
        "wind_speed_unit": "mph"})
    hours = _hours(forecast)
    if not hours:
        return f"There's no daylight left today in {p['name']} for {VERBS[kind]}. Ask me about tomorrow."
    for h in hours:
        h["score"] = score(h["temp"], h["pop"], h["mm"], h["wind"], h["gust"], low, high)
    pairs = [(hours[i:i + 2], sum(h["score"] for h in hours[i:i + 2]) / len(hours[i:i + 2]))
             for i in range(max(1, len(hours) - 1))]
    window, avg = max(pairs, key=lambda x: x[1])
    verdict = "Yes, good" if avg >= GOOD else "It's okay" if avg >= OKAY else "Not great"
    temp = sum(h["temp"] for h in window) / len(window)
    rain = max(h["pop"] for h in window)
    wind = sum(h["wind"] for h in window) / len(window)
    start, end = window[0]["time"], f"{int(window[-1]['time'][:2]) + 1:02d}:00"
    uv = ((forecast.get("daily") or {}).get("uv_index_max") or [None])[0]
    summary = (f"{verdict} weather for {VERBS[kind]} in {p['name']}: best {start} to {end}, about {temp:.0f} degrees, "
               f"{rain:.0f}% chance of rain and {_wind_word(wind)}.{_uv_note(uv)}")
    card = screen.card("chart", f"{kind.title()} weather, {p['name']}", f"active-weather-{kind}",
                       chart={"type": "bar", "labels": [h["time"] for h in hours],
                              "values": [h["score"] for h in hours], "unit": "/100"},
                       text=f"Score out of 100 for each hour. {summary}",
                       buttons=[{"label": n.title(), "say": f"Is it good weather for {v} today?"}
                                for n, v in VERBS.items() if n != kind])
    return screen.Shown(summary, card)


def kit(args: dict) -> screen.Shown:
    text = store.clean(args.get("trip")).lower().replace("_", " ") or "day walk"
    key = text if text in data.KITS else data.KIT_ALIASES.get(text) or next(
        (v for k, v in data.KIT_ALIASES.items() if k in text), None)
    if not key:
        raise ValueError("I have kit lists for a day walk, hill walk, winter hill day and an overnight trip.")
    title, items = data.KITS[key]
    card = screen.card("list", title, f"active-kit-{key.replace(' ', '-')}", checks=True,
                       items=[{"label": i} for i in items],
                       buttons=[{"label": "Hill safety", "say": "Give me the hill walking safety checklist"}])
    return screen.Shown(f"{title}: {len(items)} things to pack. Tick them off on the screen.", card)


def countryside_code() -> screen.Shown:
    lines = []
    for heading, points in data.COUNTRYSIDE_CODE:
        lines += [heading.upper()] + [f"- {p}" for p in points] + [""]
    card = screen.card("text", "The Countryside Code", "active-countryside", text="\n".join(lines) + data.COUNTRYSIDE_NOTE)
    return screen.Shown("The Countryside Code: respect everyone, protect the environment and enjoy the outdoors. "
                        "The full points are on the screen.", card)


def hill_safety() -> screen.Shown:
    card = screen.card("list", "Hill walking safety", "active-hill-safety", checks=True,
                       items=[{"label": i} for i in data.HILL_SAFETY],
                       buttons=[{"label": "Kit list", "say": "Give me the hill walking kit list"}])
    return screen.Shown("The hill walking safety checklist is on the screen. In an emergency, dial 999 and ask for "
                        "Police, then Mountain Rescue.", card)


def _routes(settings: Settings) -> list[dict]:
    return store.section(settings, "routes", [])


def route_save(settings: Settings, args: dict) -> str:
    routes = _routes(settings)
    name = store.need(args.get("name"), "route name", 60)
    km = store.km_from(args["distance"], args.get("unit")) if args.get("distance") not in (None, "") else 0
    kind = CANON.get(store.clean(args.get("kind")).lower(), store.clean(args.get("kind")).lower()) or "walk"
    old = next((r for r in routes if r["name"].lower() == name.lower()), None)
    entry = {"name": name, "km": round(km, 2), "kind": kind, "note": store.clean(args.get("note"), 300)}
    if old:
        old.update({k: v for k, v in entry.items() if v})
    else:
        if len(routes) >= 100:
            raise ValueError("That's 100 routes; remove some first.")
        routes.append(entry)
    store.save_section(settings, "routes", routes)
    return f"{'Updated' if old else 'Saved'} the route {name}" + (f", {store.dist_text(km)}." if km else ".")


def route_list(settings: Settings) -> str | screen.Shown:
    routes = _routes(settings)
    if not routes:
        return "No routes saved yet. Say something like 'Save my route Ilkley Moor, 8 km, muddy after rain'."
    rows = [[r["name"], f"{r['km']:.1f} km" if r["km"] else "", r["kind"], r.get("note", "")] for r in routes]
    card = screen.card("table", "My routes", "active-routes", columns=["Route", "Distance", "Type", "Notes"], rows=rows,
                       buttons=[{"label": f"Log {r['name']}"[:40], "say": f"Log a {r['kind']} on my {r['name']} route"}
                                for r in routes[:4]])
    return screen.Shown(f"You have {store.plural(len(routes), 'saved route')}. They're on the screen.", card)


def route_remove(settings: Settings, args: dict) -> str:
    routes = _routes(settings)
    name = store.need(args.get("name"), "route name", 60).lower()
    found = next((r for r in routes if name in r["name"].lower()), None)
    if not found:
        raise ValueError(f"I can't find a route called {name}.")
    if not args.get("confirmed"):
        return (f"That would delete the route {found['name']}. Ask the user to confirm, then call again with "
                "confirmed true.")
    store.save_section(settings, "routes", [r for r in routes if r is not found])
    return f"Removed the route {found['name']}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "active_outdoors",
        "description": "Getting outdoors in the UK. weather ('is it good weather for a run, walk, bike ride or hike "
                       "today?': kind and city; scores the hours and gives the best time, rain, wind and UV), kit (hiking "
                       "kit checklist; trip day walk, hill walk, winter or overnight), countryside_code, hill_safety "
                       "(hill-walking safety checklist), route_save (walking route with name, distance, unit, kind, "
                       "note), route_list, route_remove (confirmed true only after the user confirms).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "kind": {"type": "string", "description": "run, walk, cycle or hike."},
                "city": {"type": "string", "description": "Only a city name is sent; blank uses the home city."},
                "trip": {"type": "string", "description": "kit: day walk, hill walk, winter or overnight."},
                "name": {"type": "string", "description": "Route name."},
                "distance": {"type": "number"},
                "unit": {"type": "string", "enum": ["km", "miles"]},
                "note": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "weather":
        return await weather(http, settings, args)
    if action == "kit":
        return kit(args)
    if action == "countryside_code":
        return countryside_code()
    if action == "hill_safety":
        return hill_safety()
    if action == "route_save":
        return route_save(settings, args)
    if action == "route_list":
        return route_list(settings)
    if action == "route_remove":
        return route_remove(settings, args)
    raise ValueError(f"Unknown action {action}.")
