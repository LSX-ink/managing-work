"""Local tools Jarvis can call: weather, tasks, memory folders, opening URLs, looking at the screen."""

import asyncio
import base64
import io
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx

import aboutyou
import agenda
import alerts
import feeds
import feeds_outdoors
import filing
import habits
import health
import memory
import money
import music
import notesearch
import pc
import reminders
import shopping
import timers
import todo
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
CHAT_CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")

# Ability modules. Each has tool_definitions() -> list, NAMES (a set of tool names) and
# run_tool(name, args, settings, http) -> str | list, sync or async. Add new abilities here.
ABILITIES = [todo, habits, money, notesearch]
ABILITIES += [feeds, feeds_outdoors]  # live-info


def client_tool_definitions(settings: Settings) -> list[dict]:
    """Custom tools that run on this machine."""
    tools = [
        {
            "name": "get_weather",
            "description": "Current weather for a city, plus a forecast for the coming days when asked (tomorrow, "
                           "the weekend, the week). Defaults to the user's home city when no city is given.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. 'London'."},
                    "days": {"type": "integer", "description": "Days of forecast including today, 1 to 7. Default 1."},
                },
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
    tools.append({
        "name": "move_chat_panel",
        "description": "Move the chat panel (the conversation and typing box) on the user's screen to a corner, "
                       "or back to the centre. The page remembers it.",
        "input_schema": {
            "type": "object",
            "properties": {"position": {"type": "string", "enum": [*CHAT_CORNERS, "centre"]}},
            "required": ["position"],
            "additionalProperties": False,
        },
    })
    tools.append({
        "name": "listen_for_name",
        "description": "Turn name-only listening on or off. On: you ignore speech that doesn't use your name "
                       "(handy with the TV on or guests talking), except follow-ups within 20 seconds of your "
                       "reply. Off: you answer everything you hear. The page remembers it.",
        "input_schema": {
            "type": "object",
            "properties": {"on": {"type": "boolean"}},
            "required": ["on"],
            "additionalProperties": False,
        },
    })
    tools += aboutyou.tool_definitions()
    tools += memory.tool_definitions()
    tools.append(wishes.tool_definition())
    tools += timers.tool_definitions()
    tools += reminders.tool_definitions()
    tools += agenda.tool_definitions()
    tools += health.tool_definitions()
    tools += shopping.tool_definitions()
    for module in ABILITIES:
        tools += module.tool_definitions()
    if settings.email_enabled:
        tools.append({
            "name": "check_inbox",
            "description": "The newest emails in the user's inbox (sender, subject, when), to answer 'anything "
                           "important?' or 'did X email me?'. Summarise: pick out what matters and skip adverts "
                           "and newsletters. Read-only; nothing is marked as read.",
            "input_schema": {
                "type": "object",
                "properties": {"hours": {"type": "integer", "description": "How far back, 1 to 168. Default 24."}},
                "additionalProperties": False,
            },
        })
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
        tools += filing.tool_definitions()
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


async def get_weather(http: httpx.AsyncClient, city: str, days: int = 1) -> str:
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
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": days,
            "timezone": "auto",
        },
    )
    forecast.raise_for_status()
    data = forecast.json()
    now, daily = data["current"], data["daily"]
    sky = WEATHER_CODES.get(now["weather_code"], "unknown conditions")
    ahead = "".join(
        f" {day}: {WEATHER_CODES.get(daily['weather_code'][i], 'unknown conditions')}, high {daily['temperature_2m_max'][i]}°C, "
        f"low {daily['temperature_2m_min'][i]}°C, {daily['precipitation_probability_max'][i]}% chance of rain."
        for i, day in enumerate((date.fromisoformat(d).strftime("%A") for d in daily["time"][1:]), start=1)
    ) if days > 1 else ""
    return (
        f"{place['name']}, {place.get('country', '')}: {now['temperature_2m']}°C "
        f"(feels like {now['apparent_temperature']}°C), {sky}, wind {now['wind_speed_10m']} km/h. "
        f"Today: high {daily['temperature_2m_max'][0]}°C, low {daily['temperature_2m_min'][0]}°C, "
        f"{daily['precipitation_probability_max'][0]}% chance of rain.{ahead}"
    )


def inbox_text(settings: Settings, hours: int = 24) -> str:
    """The newest inbox emails, newest first, for Alfred to summarise."""
    cutoff = datetime.now().astimezone() - timedelta(hours=hours)
    mails = [m for m in alerts.fetch_mail(settings, days=max(1, -(-hours // 24)), limit=60)
             if not m.date or m.date >= cutoff]
    if not mails:
        return f"No emails in the last {hours} hours."
    lines = [f"- {m.date:%a %H:%M} " if m.date else "- " for m in mails]
    return f"{len(mails)} emails in the last {hours} hours, newest first:\n" + "\n".join(
        f"{when}from {m.sender}: {m.subject or '(no subject)'}" for when, m in reversed(list(zip(lines, mails))))


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
    return todo.text(settings)


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
        days = min(max(int(args.get("days") or 1), 1), 7)
        return await get_weather(http, args.get("city") or settings.city, days)
    if name == "get_tasks":
        return get_tasks(settings)
    if name == "open_url":
        return await open_url(args["url"])
    if name in filing.NAMES and settings.email_enabled:
        return await filing.run_tool(name, args, settings)
    if name in aboutyou.NAMES:
        return await asyncio.to_thread(aboutyou.run_tool, name, args, settings)
    if name == "check_inbox" and settings.email_enabled:
        hours = min(max(int(args.get("hours") or 24), 1), 168)
        return await asyncio.to_thread(inbox_text, settings, hours)
    if name in health.NAMES:
        return await asyncio.to_thread(health.run_tool, name, settings)
    if name in agenda.NAMES:
        days = min(max(int(args.get("days") or 1), 1), 31)
        return await agenda.upcoming(http, settings, days)
    for module in ABILITIES:
        if name in module.NAMES:
            if asyncio.iscoroutinefunction(module.run_tool):
                return await module.run_tool(name, args, settings, http)
            return await asyncio.to_thread(module.run_tool, name, args, settings, http)
    if name in shopping.NAMES:
        return await asyncio.to_thread(shopping.run_tool, args, settings)
    if name in reminders.NAMES:
        return await asyncio.to_thread(reminders.run_tool, name, args, settings)
    if name in timers.NAMES:
        return timers.run_tool(name, args, settings)
    if name == "listen_for_name":
        if not page:
            return "The Jarvis page isn't open."
        await page({"type": "wakeword", "on": bool(args.get("on"))})
        return ("Now only answering when called by name (follow-ups within 20 seconds are fine)."
                if args.get("on") else "Now answering everything I hear.")
    if name == "move_chat_panel":
        position = args.get("position")
        if position not in (*CHAT_CORNERS, "centre"):
            raise ValueError("Pick top-left, top-right, bottom-left, bottom-right or centre.")
        if not page:
            return "The Jarvis page isn't open, so there's no chat panel to move."
        await page({"type": "chat", "corner": position})
        return f"Moved the chat panel to the {position.replace('-', ' ')}."
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
        six = {n.lower() for n in memory.names(settings)}
        inner = path.parent != memory.root(settings).resolve() or path.name.lower() not in six  # a star, not a wolf part
        if args.get("on_pc") or inner or not settings.theme.startswith("hud"):  # the HUD panel shows the six
            if inner and page:  # its star on the HUD flares as it opens
                await page({"type": "memory", "star": path.relative_to(memory.root(settings).resolve()).as_posix()})
            await asyncio.to_thread(pc.launch, path)
            return f"Opened the {path.name} folder in File Explorer."
        if not page:
            return "The Jarvis page isn't open, so there's nowhere to show the folder."
        await page({"type": "memory", "open": path.name})
        return f"Opened the {path.name} folder on the HUD."
    if name in ("save_to_memory", "read_memory", "create_memory_folder", "delete_memory_folder", "read_document"):
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
