"""Outdoor conditions from keyless feeds: air quality, pollen, UV, rain soon, washing-drying weather,
aurora chances (NOAA Kp index) and UK grid carbon intensity.

Only a city name goes to Open-Meteo's geocoder; the rest is coordinates or nothing at all.
"""

import httpx

from config import Settings
from feeds import fetch_json

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"
KP = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
CARBON = "https://api.carbonintensity.org.uk/intensity"

AQI_BANDS = [(20, "good"), (40, "fair"), (60, "moderate"), (80, "poor"), (100, "very poor")]
POLLEN_BANDS = [(1, "none"), (20, "low"), (50, "moderate"), (200, "high")]
UV_BANDS = [
    (3, "low", "no protection needed"),
    (6, "moderate", "sunscreen and sunglasses if you're out for long, and shade around midday"),
    (8, "high", "sunscreen, a hat and sunglasses, and shade between 11 and 3"),
    (11, "very high", "avoid the midday sun, cover up and use high-factor sunscreen"),
]
CARBON_ADVICE = {
    "very low": "Yes, it's a great time to run the washing machine.",
    "low": "Yes, it's a good time to run the washing machine.",
    "moderate": "It's an average time. Fine if you need to, but later could be greener.",
    "high": "Better to wait if you can; the grid is fairly dirty right now.",
    "very high": "Best to wait; the grid is very carbon-heavy right now.",
}


def _band(value: float, bands: list, top: str) -> str:
    for limit, word in bands:
        if value < limit:
            return word
    return top


async def place(http: httpx.AsyncClient, city: str) -> dict:
    """The first Open-Meteo geocoder match for a city, as in tools.get_weather."""
    if not city:
        raise ValueError("No city given and no home city configured (set JARVIS_CITY).")
    geo = await fetch_json(http, GEOCODE, "place lookup",
                           params={"name": city, "count": 1, "language": "en", "format": "json"})
    places = geo.get("results") or []
    if not places:
        raise ValueError(f"Could not find a place called {city!r}.")
    return places[0]


def _where(p: dict) -> dict:
    return {"latitude": p["latitude"], "longitude": p["longitude"], "timezone": "auto"}


async def air_quality(http: httpx.AsyncClient, p: dict) -> str:
    now = (await fetch_json(http, AIR, "air quality", params={
        **_where(p), "current": "european_aqi,pm2_5,pm10"})).get("current") or {}
    aqi = now.get("european_aqi")
    if aqi is None:
        return f"No air quality reading for {p['name']} right now."
    return (f"Air quality in {p['name']} is {_band(aqi, AQI_BANDS, 'extremely poor')} (European index {aqi:g}). "
            f"PM2.5 {now.get('pm2_5')} and PM10 {now.get('pm10')} micrograms per cubic metre.")


async def pollen(http: httpx.AsyncClient, p: dict) -> str:
    kinds = ("grass", "birch", "alder")
    now = (await fetch_json(http, AIR, "pollen", params={
        **_where(p), "current": ",".join(f"{k}_pollen" for k in kinds)})).get("current") or {}
    found = {k: now.get(f"{k}_pollen") for k in kinds if now.get(f"{k}_pollen") is not None}
    if not found:
        return f"There's no pollen forecast for {p['name']}; it's only available in Europe."
    return f"Pollen in {p['name']} now: " + ", ".join(
        f"{k} {_band(v, POLLEN_BANDS, 'very high')} ({v:g} grains per cubic metre)" for k, v in found.items()) + "."


async def uv(http: httpx.AsyncClient, p: dict) -> str:
    daily = (await fetch_json(http, FORECAST, "UV forecast", params={
        **_where(p), "daily": "uv_index_max", "forecast_days": 1})).get("daily") or {}
    value = (daily.get("uv_index_max") or [None])[0]
    if value is None:
        return f"No UV forecast for {p['name']} today."
    for limit, word, advice in UV_BANDS:
        if value < limit:
            break
    else:
        word, advice = "extreme", "stay out of the midday sun and cover up fully"
    return f"Today's highest UV index in {p['name']} is {value:g}, which is {word}: {advice}."


async def _hours(http: httpx.AsyncClient, p: dict, fields: str, hours: int, what: str) -> dict:
    return (await fetch_json(http, FORECAST, what, params={
        **_where(p), "hourly": fields, "forecast_hours": hours})).get("hourly") or {}


async def rain(http: httpx.AsyncClient, p: dict, hours: int) -> str:
    hourly = await _hours(http, p, "precipitation_probability,precipitation", hours, "rain forecast")
    chances = [c or 0 for c in hourly.get("precipitation_probability") or []]
    if not chances:
        return f"No rain forecast for {p['name']} right now."
    peak = max(chances)
    when = (hourly.get("time") or [""] * len(chances))[chances.index(peak)][11:16]
    total = sum(x or 0 for x in hourly.get("precipitation") or [])
    if peak >= 60:
        verdict = "Yes, take an umbrella."
    elif peak >= 30:
        verdict = "Maybe; a small umbrella wouldn't hurt."
    else:
        verdict = "No, you shouldn't need an umbrella."
    return (f"{verdict} In {p['name']} over the next {len(chances)} hours the highest chance of rain is "
            f"{peak}%" + (f" around {when}" if when and peak else "") + f", with {total:.1f} mm expected in all.")


async def drying(http: httpx.AsyncClient, p: dict, hours: int) -> str:
    hourly = await _hours(http, p, "relative_humidity_2m,wind_speed_10m,precipitation_probability,temperature_2m",
                          hours, "drying forecast")
    hum = [h for h in hourly.get("relative_humidity_2m") or [] if h is not None]
    wind = [w for w in hourly.get("wind_speed_10m") or [] if w is not None]
    wet = [c or 0 for c in hourly.get("precipitation_probability") or []]
    temp = [t for t in hourly.get("temperature_2m") or [] if t is not None]
    if not (hum and wind and wet):
        return f"No drying forecast for {p['name']} right now."
    avg_hum, avg_wind = sum(hum) / len(hum), sum(wind) / len(wind)
    if max(wet) >= 40:
        verdict = "Not a good day for drying outside: rain is likely."
    elif avg_hum < 70 and avg_wind >= 10:
        verdict = "Good drying weather: breezy and fairly dry."
    elif avg_hum < 85:
        verdict = "Okay for drying, but it'll be slow."
    else:
        verdict = "Poor drying weather: it's too damp."
    warmth = f", around {sum(temp) / len(temp):.0f}°C" if temp else ""
    return (f"{verdict} Next {len(hum)} hours in {p['name']}: wind about {avg_wind:.0f} km/h (up to "
            f"{max(wind):.0f}), humidity about {avg_hum:.0f}%, rain chance up to {max(wet)}%{warmth}.")


def latest_kp(body) -> tuple[str, float]:
    """(time, Kp) of the newest row; NOAA serves either objects or a header row plus lists."""
    rows = body if isinstance(body, list) else []
    if rows and isinstance(rows[0], list):
        head = [str(h).lower() for h in rows[0]]
        col = head.index("kp") if "kp" in head else 1
        rows = [{"time_tag": r[0], "Kp": r[col]} for r in rows[1:] if isinstance(r, list) and len(r) > col]
    for row in reversed(rows):
        value = row.get("Kp", row.get("kp_index")) if isinstance(row, dict) else None
        try:
            return str(row.get("time_tag") or ""), float(value)
        except (TypeError, ValueError):
            continue
    raise ValueError("The space weather service sent nothing I could read.")


async def aurora(http: httpx.AsyncClient) -> str:
    when, kp = latest_kp(await fetch_json(http, KP, "NOAA space weather"))
    if kp >= 7:
        verdict = "A strong storm: the northern lights could be seen across much of the UK on a clear dark night."
    elif kp >= 6:
        verdict = "Good chances in Scotland and northern England, and maybe further south with a dark sky."
    elif kp >= 5:
        verdict = "A chance in Scotland and possibly the far north of England."
    elif kp >= 4:
        verdict = "Only a slim chance, mostly in northern Scotland away from lights."
    else:
        verdict = "Quiet: the northern lights are unlikely to be visible from the UK."
    stamp = f" (reading from {when[:16].replace('T', ' ')} UTC)" if when else ""
    return f"The planetary K-index is {kp:g}{stamp}. {verdict}"


async def carbon(http: httpx.AsyncClient) -> str:
    rows = (await fetch_json(http, CARBON, "Carbon Intensity")).get("data") or []
    if not rows:
        return "The UK carbon intensity service has no reading right now."
    info = rows[0].get("intensity") or {}
    index = str(info.get("index") or "").lower()
    value = info.get("actual") if info.get("actual") is not None else info.get("forecast")
    advice = CARBON_ADVICE.get(index, "")
    return f"UK grid carbon intensity is {index or 'unknown'} right now ({value} grams of CO2 per kWh). {advice}".strip()


def tool_definitions() -> list[dict]:
    return [{
        "name": "outdoors",
        "description": "Outdoor conditions now, for a city (defaults to home). kind: 'air_quality', 'pollen', "
                       "'uv' (today's peak with advice), 'rain' (do I need an umbrella in the next hours), "
                       "'drying' (wind and whether washing will dry outside), 'aurora' (northern lights chance "
                       "in the UK), 'carbon' (UK grid carbon now: good time to run the washing machine?).",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["air_quality", "pollen", "uv", "rain", "drying", "aurora",
                                                    "carbon"]},
                "city": {"type": "string", "description": "City name, e.g. 'Leeds'."},
                "hours": {"type": "integer", "description": "Hours ahead for rain or drying, 1 to 12. Default 6."},
            },
            "required": ["kind"],
            "additionalProperties": False,
        },
    }]


NAMES = {"outdoors"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient) -> str:
    kind = args.get("kind")
    if kind == "aurora":
        return await aurora(http)
    if kind == "carbon":
        return await carbon(http)
    if kind not in ("air_quality", "pollen", "uv", "rain", "drying"):
        raise ValueError("Pick air_quality, pollen, uv, rain, drying, aurora or carbon.")
    try:
        hours = min(max(int(args.get("hours") or 6), 1), 12)
    except (TypeError, ValueError):
        hours = 6
    p = await place(http, (args.get("city") or settings.city).strip())
    if kind == "air_quality":
        return await air_quality(http, p)
    if kind == "pollen":
        return await pollen(http, p)
    if kind == "uv":
        return await uv(http, p)
    if kind == "rain":
        return await rain(http, p, hours)
    return await drying(http, p, hours)
