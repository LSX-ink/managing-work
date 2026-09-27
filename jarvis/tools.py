"""Local tools Jarvis can call: weather, tasks, memory folders, opening URLs, looking at the screen."""

import asyncio
import base64
import io
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

import httpx

import alerts
import memory
import music
import pc
import wishes
from config import Settings

# Open-Meteo WMO weather codes -> words (https://open-meteo.com/en/docs)
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "heavy freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}

# Longest edge of a screenshot sent to Claude; larger images are downscaled anyway.
SCREEN_MAX_EDGE = 1568


def client_tool_definitions(settings: Settings) -> list[dict]:
    """Custom tools that run on this machine."""
    tools = [
        {
            "name": "get_weather",
            "description": "Current weather for a city. Defaults to the user's home city when no city is given.",
            "input_schema": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City name, e.g. 'London'."}},
                "additionalProperties": False,
            },
        },
        {
            "name": "get_tasks",
            "description": "The user's open to-do items from their Markdown task list.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "open_url",
            "description": "Open a web page in the user's own browser so they can see it. Only http(s) URLs.",
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Full http(s) URL."}},
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    ]
    tools += memory.tool_definitions()
    tools.append(wishes.tool_definition())
    if settings.email_enabled:
        tools.append({
            "name": "check_deliveries",
            "description": "Order and delivery emails (Deliveroo, Just Eat, Uber Eats, Amazon, couriers) from the "
                           "user's inbox in the last few days, with when they arrived.",
            "input_schema": {
                "type": "object",
                "properties": {"days": {"type": "integer", "description": "How many days back, 1 to 14. Default 3."}},
                "additionalProperties": False,
            },
        })
    if settings.enable_pc:
        tools += pc.tool_definitions()
        tools.append(music.tool_definition())
    if settings.enable_screen and not settings.enable_computer:  # the computer toolset has its own screenshot
        tools.append({
            "name": "look_at_screen",
            "description": "Take a screenshot of the user's screen so you can see what they are looking at.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        })
    return tools


async def get_weather(http: httpx.AsyncClient, city: str) -> str:
    if not city:
        return "No city given and no home city configured (set JARVIS_CITY)."
    geo = await http.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "en", "format": "json"},
    )
    geo.raise_for_status()
    places = geo.json().get("results") or []
    if not places:
        return f"Could not find a place called {city!r}."
    place = places[0]
    forecast = await http.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 1,
            "timezone": "auto",
        },
    )
    forecast.raise_for_status()
    data = forecast.json()
    now, daily = data["current"], data["daily"]
    sky = WEATHER_CODES.get(now["weather_code"], "unknown conditions")
    return (
        f"{place['name']}, {place.get('country', '')}: {now['temperature_2m']}°C "
        f"(feels like {now['apparent_temperature']}°C), {sky}, wind {now['wind_speed_10m']} km/h. "
        f"Today: high {daily['temperature_2m_max'][0]}°C, low {daily['temperature_2m_min'][0]}°C, "
        f"{daily['precipitation_probability_max'][0]}% chance of rain."
    )


def read_open_tasks(tasks_file: str) -> list[str]:
    """Unchecked Markdown checkboxes (`- [ ] ...`) from a file, e.g. an Obsidian note."""
    if not tasks_file:
        return []
    path = Path(tasks_file).expanduser()
    if not path.is_file():
        return []
    tasks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        for prefix in ("- [ ]", "* [ ]"):
            if stripped.startswith(prefix):
                text = stripped[len(prefix):].strip()
                if text:
                    tasks.append(text)
    return tasks


def get_tasks(settings: Settings) -> str:
    if not settings.tasks_file:
        return "No task list configured (set JARVIS_TASKS_FILE)."
    tasks = read_open_tasks(settings.tasks_file)
    if not tasks:
        return "No open tasks."
    return f"{len(tasks)} open tasks:\n" + "\n".join(f"- {t}" for t in tasks)


def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


async def open_url(url: str) -> str:
    if not is_safe_url(url):
        return f"Refused to open {url!r}: only http(s) URLs are allowed."
    await asyncio.to_thread(webbrowser.open, url)
    return f"Opened {url} in the user's browser."


def capture_screen_jpeg() -> bytes:
    from PIL import Image, ImageGrab  # imported lazily: optional on headless machines

    image = ImageGrab.grab(all_screens=True).convert("RGB")
    image.thumbnail((SCREEN_MAX_EDGE, SCREEN_MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


async def look_at_screen() -> list[dict]:
    jpeg = await asyncio.to_thread(capture_screen_jpeg)
    return [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()},
        },
        {"type": "text", "text": "Screenshot of the user's screen, taken just now."},
    ]


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient, page=None) -> str | list[dict]:
    """Execute one client tool. Raises on failure; the caller reports it as an error result."""
    if name == "get_weather":
        return await get_weather(http, args.get("city") or settings.city)
    if name == "get_tasks":
        return get_tasks(settings)
    if name == "open_url":
        return await open_url(args["url"])
    if name == "request_new_ability":
        return await wishes.request(http, settings, args["title"], args["details"])
    if name == "download_file":
        try:
            path = await memory.download(settings, http, args["folder"], args["url"], args.get("filename") or "")
        except httpx.HTTPError as e:
            raise ValueError(f"The download failed: {e}") from None
        return f"Downloaded {path.name} ({path.stat().st_size:,} bytes) into the {path.parent.name} folder."
    if name == "open_memory_folder":
        path = (await asyncio.to_thread(memory.folder, settings, args["folder"])).resolve()
        inner = path.parent != memory.root(settings).resolve()  # a folder made inside one of the six
        if args.get("on_pc") or inner or not settings.theme.startswith("hud"):  # the HUD panel shows the six
            await asyncio.to_thread(pc.launch, path)
            return f"Opened the {path.name} folder in File Explorer."
        if not page:
            return "The Jarvis page isn't open, so there's nowhere to show the folder."
        await page({"type": "memory", "open": path.name})
        return f"Opened the {path.name} folder on the HUD."
    if name in ("save_to_memory", "read_memory", "create_memory_folder"):
        return await asyncio.to_thread(memory.run_tool, name, args, settings)
    if name == "check_deliveries" and settings.email_enabled:
        days = min(max(int(args.get("days") or 3), 1), 14)
        return await asyncio.to_thread(alerts.recent_deliveries, settings, days)
    if name == "look_at_screen" and settings.enable_screen:
        return await look_at_screen()
    if name == "apple_music" and settings.enable_pc:
        return await music.apple_music(http, settings, args["query"], args.get("kind") or "song")
    if name in pc.NAMES and settings.enable_pc:
        return await asyncio.to_thread(pc.run, name, args)
    raise ValueError(f"Unknown tool: {name}")
