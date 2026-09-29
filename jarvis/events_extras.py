"""Event extras: the Christmas dinner timetable, kids' party timeline and party bags, a memory note saved after the
event, and the weather on the day from Open-Meteo's keyless forecast (a city name only, within 14 days).
"""

from datetime import date, datetime, timedelta

import events_data as data
import events_store as store
import homestore as hs
import memory
import screen
import webview_common as web
from config import Settings
from feeds import fetch_json

ACTIONS = ["christmas_dinner", "kids_party", "party_bags", "memory_note", "weather"]
FORECAST = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 14
RAIN = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
WORDS = {0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog", 71: "snow", 73: "snow",
         75: "heavy snow", 77: "snow", 85: "snow showers", 86: "snow showers", 95: "thunderstorms", 96: "thunderstorms",
         99: "thunderstorms"}


def _clock(value, default: str) -> datetime:
    text = hs.clean(value) or default
    try:
        return datetime.strptime(text, "%H:%M")
    except ValueError:
        raise ValueError("Give the time as HH:MM, like 13:30.") from None


def _timeline(title: str, card_id: str, steps: list[tuple[datetime, str]], note: str, buttons=None) -> dict:
    items = [{"when": f"{t:%H:%M}", "date": "", "text": text, "state": "", "say": ""} for t, text in sorted(steps)]
    return screen.card("events-timeline", title, card_id, buttons=buttons, data={"items": items, "note": note})


def christmas_dinner(args: dict) -> screen.Shown:
    serve = _clock(args.get("serve_at"), "13:30")
    kg = hs.number(args.get("turkey_kg", 5), "turkey weight in kilos", 1, 15)
    cook = round((20 * kg + 90) / 5) * 5
    out = serve - timedelta(minutes=60)
    turkey_in = out - timedelta(minutes=cook)
    steps = [(serve + timedelta(minutes=m), text) for m, text in data.XMAS]
    steps += [(turkey_in - timedelta(minutes=60), "Turkey out of the fridge to come up to room temperature"),
              (turkey_in - timedelta(minutes=20), "Oven on to 190 C (170 C fan)"),
              (turkey_in, f"Turkey in ({kg:g} kg, about {cook // 60} h {cook % 60} min)"),
              (out, "Turkey out to rest under foil; juices should run clear")]
    note = f"Serving at {serve:%H:%M}. Check the thickest part reaches 70 C; the rest keeps it hot."
    card = _timeline("Christmas dinner timetable", "events-xmas-dinner", steps, note)
    return screen.Shown(f"For dinner at {serve:%H:%M}, the {kg:g} kilo turkey goes in at {turkey_in:%H:%M}.", card)


def _band(age: int) -> tuple[str, list[str]]:
    for top, title, ideas in data.KIDS:
        if age <= top:
            return title, ideas
    return data.KIDS[-1][1], data.KIDS[-1][2]


def kids_party(args: dict) -> screen.Shown:
    age = int(hs.number(args.get("age"), "child's age", 1, 18))
    start = _clock(args.get("start_at"), "14:00")
    title, ideas = _band(age)
    scale = 1 if age > 2 else 0.75
    steps = [(start + timedelta(minutes=round(m * scale)), text) for m, text in data.KIDS_STEPS]
    card = _timeline(f"Party for a {age} year old", f"events-kids-{age}", steps, f"Ideas for {title}: " + "; ".join(ideas),
                     [store.button("Party bag list", f"Make a party bag list for {args.get('children', 10)} children.")])
    return screen.Shown(f"A party for a {age} year old starting at {start:%H:%M}: {ideas[1].lower()}.", card)


def party_bags(args: dict) -> screen.Shown:
    kids = int(hs.number(args.get("children", 10), "number of children", 1, 100))
    items = [{"label": f"{item}: {kids}", "done": False} for item in data.BAGS]
    return screen.Shown(f"Party bags for {kids} children: {len(items)} things to buy.",
                        screen.card("list", f"Party bags for {kids}", "events-bags", items=items, checks=True))


def memory_note(settings: Settings, args: dict, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), args.get("name"), today)
    text = hs.need(args.get("note"), "memory to save", 4000)
    day = date.fromisoformat(event["date"])
    body = f"{key}, {hs.spoken(day)} {day.year}\n{event['place'] + chr(10) if event['place'] else ''}\n{text}\n"
    path = memory.save_note(settings, "Personal", f"Memories {key} {day.year}", body)
    return screen.Shown(f"Saved your memory of {key} in your Personal folder.", screen.file_card(settings, path))


async def weather(http, settings: Settings, args: dict, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), args.get("name"), today)
    day = date.fromisoformat(event["date"])
    ahead = (day - today).days
    if ahead < 0:
        raise ValueError(f"{key} has already happened.")
    if ahead > FORECAST_DAYS:
        raise ValueError(f"{key} is {ahead} days away and forecasts only reach {FORECAST_DAYS} days. Ask me nearer the time.")
    place = await web.geocode(http, hs.clean(args.get("city")) or event["place"] or settings.city)
    body = await fetch_json(http, FORECAST, "forecast", {
        "latitude": place["lat"], "longitude": place["lon"], "timezone": "auto", "forecast_days": FORECAST_DAYS + 2,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max"})
    daily = (body.get("daily") or {}) if isinstance(body, dict) else {}
    if day.isoformat() not in (daily.get("time") or []):
        raise ValueError("The forecast didn't cover that day. Try again in a bit.")
    i = daily["time"].index(day.isoformat())
    code, hi, lo = daily["weathercode"][i], daily["temperature_2m_max"][i], daily["temperature_2m_min"][i]
    rain, wind = daily["precipitation_probability_max"][i], daily["wind_speed_10m_max"][i]
    words = "rain" if code in RAIN else WORDS.get(code, "changeable")
    advice = "Plan an indoor backup or a marquee." if code in RAIN or (rain or 0) >= 50 else \
        "Windy for outdoor decorations." if (wind or 0) >= 35 else "Looks good for the day."
    rows = [["Weather", words], ["High / low", f"{hi:g} / {lo:g} C"], ["Chance of rain", f"{rain}%"],
            ["Wind", f"{wind:g} km/h"], ["Advice", advice]]
    return screen.Shown(f"{key} in {place['name']}: {words}, {hi:g} degrees, {rain}% chance of rain. {advice}",
                        screen.card("table", f"{key}: weather", f"events-weather-{key}", columns=["", hs.spoken(day)], rows=rows))


def tool_definitions() -> list[dict]:
    return [{
        "name": "event_extras",
        "description": "Event extras. action: christmas_dinner = Christmas dinner cooking timetable working back "
                       "from serving time (serve_at, turkey_kg) as a timeline pop-up; kids_party = age-appropriate "
                       "kids' party timeline (age, start_at); party_bags = party bag list for the children; "
                       "memory_note = save a photo or memory note after the event to the memory folder; weather = "
                       "forecast for the event day (only within 14 days; sends the city only).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "The event; may be left out for the next one."},
                "serve_at": {"type": "string", "description": "HH:MM, default 13:30."},
                "turkey_kg": {"type": "number"},
                "age": {"type": "integer"},
                "start_at": {"type": "string", "description": "HH:MM, default 14:00."},
                "children": {"type": "integer"},
                "note": {"type": "string", "description": "memory_note: what to remember."},
                "city": {"type": "string", "description": "weather: default the event place or home city."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"event_extras"}


async def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    if action == "christmas_dinner":
        return christmas_dinner(args)
    if action == "kids_party":
        return kids_party(args)
    if action == "party_bags":
        return party_bags(args)
    if action == "memory_note":
        return memory_note(settings, args, today)
    if action == "weather":
        return await weather(http, settings, args, today)
    raise ValueError(f"Unknown event extras action: {action}")
