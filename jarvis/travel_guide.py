"""Travel know-how: a 20-phrase phrasebook in 10 languages with a Speak button, plugs and voltage, driving side,
emergency numbers and tipping for about 70 countries, a jet lag bedtime planner and good times to call home.

The tables are local (travel_data.py). Time zones come from zoneinfo; only a place name the city list doesn't know
goes to Open-Meteo's geocoder to find its zone.
"""

from datetime import date, datetime, timedelta

import httpx

import dates
import homestore as hs
import screen
import travel_data
import travel_store as ts
from config import Settings

screen.EXTRA_KINDS.add("travel-phrases")
HOME_PLUG, HOME_VOLTS = "G", "230"
AWAKE = range(8, 22)  # hours when a call is fine at both ends

ACTIONS = ["phrases", "plugs", "customs", "jetlag", "call_times"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "travel_guide",
        "description": "Travel phrasebook and country facts. phrases: essential phrases (hello, thank you, the bill, "
                       "where is the toilet...) in French, Spanish, Italian, German, Portuguese, Dutch, Greek, "
                       "Turkish, Japanese or Mandarin, with a Speak button, or one phrase translated; plugs: plug "
                       "type and voltage, do I need an adapter; customs: which side they drive on, the emergency "
                       "number and tipping; jetlag: a bedtime plan shifting an hour a day before flying across time "
                       "zones; call_times: the time difference and good times to call home from a trip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "language": {"type": "string", "description": "phrases: the language or country."},
                "phrase": {"type": "string", "description": "phrases: one English phrase to translate."},
                "country": {"type": "string", "description": "plugs, customs: a country, or 'all' for the table."},
                "destination": {"type": "string", "description": "jetlag, call_times: city or zone there."},
                "trip": {"type": "string", "description": "A saved trip instead of a destination."},
                "home": {"type": "string", "description": "Home city; default the user's city."},
                "day": {"type": "string", "description": "jetlag: flight day, YYYY-MM-DD; default the trip start."},
                "days": {"type": "integer", "description": "jetlag: days to adjust before flying, 1 to 7 (3)."},
                "bedtime": {"type": "string", "description": "jetlag: usual bedtime HH:MM (23:00)."},
                "wake": {"type": "string", "description": "jetlag: usual wake time HH:MM (07:00)."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"travel_guide"}


# ---- phrasebook --------------------------------------------------------------------------

def language(value) -> str:
    text = hs.clean(value).lower()
    for name in travel_data.LANGUAGES:
        if name.lower() == text:
            return name
    if text in travel_data.LANGUAGE_ALIASES:
        return travel_data.LANGUAGE_ALIASES[text]
    raise ValueError(f"The phrasebook has {', '.join(travel_data.LANGUAGES)}.")


def _pair(value) -> tuple[str, str]:
    return value if isinstance(value, tuple) else (value, "")


def phrases(args: dict) -> screen.Shown | str:
    lang = language(args.get("language"))
    want = hs.clean(args.get("phrase")).lower().strip("?!. ")
    if want:
        hit = next((p for p in travel_data.PHRASES if p[0].lower().strip("?!. ") == want), None) or next(
            (p for p in travel_data.PHRASES if want in p[0].lower()), None)
        if not hit:
            return f"That isn't in the phrasebook. The phrases are: {', '.join(p[0] for p in travel_data.PHRASES)}."
        phrase, sound = _pair(hit[1][lang])
        return f"In {lang}, '{hit[0]}' is {phrase}" + (f", said {sound}." if sound else ".")
    rows = []
    for english, by_lang in travel_data.PHRASES:
        phrase, sound = _pair(by_lang[lang])
        rows.append({"en": english, "phrase": phrase, "sound": sound,
                     "say": f"How do I say '{english}' in {lang}? Say it slowly."})
    data = {"language": lang, "lang": travel_data.LANGUAGES[lang], "rows": rows}
    return screen.Shown(f"The {lang} phrasebook is on the screen; press Speak to hear one.", screen.card(
        "travel-phrases", f"{lang} phrasebook", f"travel-phrases-{lang}", data=data))


# ---- country facts -----------------------------------------------------------------------

def _either(plugs: str) -> str:
    first, _, last = plugs.rpartition(", ")
    return f"{first} or {last}" if first else last


def _adapter(plugs: str, volts: str) -> str:
    types = [p.strip() for p in plugs.split(",")]
    adapter = "Same plugs as the UK, no adapter needed." if HOME_PLUG in types else \
        f"You'll need a travel adapter for type {types[0]} sockets."
    if volts == HOME_VOLTS or volts.startswith("2"):
        return adapter
    return adapter + f" The mains is {volts} volts: chargers marked 100-240 V are fine, but UK hair dryers and " \
                     "straighteners may not work."


def plugs(args: dict) -> screen.Shown:
    if hs.clean(args.get("country")).lower() in ("", "all", "every country"):
        rows = [[c, v[0], f"{v[1]} V {v[2]} Hz"] for c, v in travel_data.COUNTRIES.items()]
        return screen.Shown(f"Plugs and voltage for {len(rows)} countries are on the screen.", screen.card(
            "table", "Plugs and voltage", "travel-plugs", columns=["Country", "Plug types", "Mains"], rows=rows))
    name = ts.country(args.get("country"))
    plug, volts, hz, *_ = travel_data.COUNTRIES[name]
    said = f"{name} uses type {_either(plug)} plugs at {volts} volts, {hz} Hz. {_adapter(plug, volts)}"
    return screen.Shown(said, screen.card(
        "table", f"Plugs: {name}", f"travel-plugs-{name}", columns=["", name],
        rows=[["Plug types", plug], ["Voltage", f"{volts} V"], ["Frequency", f"{hz} Hz"],
              ["From the UK", _adapter(plug, volts)]]))


def customs(args: dict) -> screen.Shown:
    if hs.clean(args.get("country")).lower() in ("", "all", "every country"):
        rows = [[c, v[3], v[4], v[5]] for c, v in travel_data.COUNTRIES.items()]
        return screen.Shown(f"Driving side, emergency numbers and tipping for {len(rows)} countries are on the screen.",
                            screen.card("table", "Country customs", "travel-customs",
                                        columns=["Country", "Drive on", "Emergency", "Tipping"], rows=rows))
    name = ts.country(args.get("country"))
    _, _, _, side, sos, tip = travel_data.COUNTRIES[name]
    said = f"In {name} they drive on the {side}. Emergency number: {sos}. Tipping: {tip}."
    return screen.Shown(said, screen.card(
        "table", f"{name} customs", f"travel-customs-{name}", columns=["", name],
        rows=[["Drive on the", side], ["Emergency", sos], ["Tipping", tip]]))


# ---- time zones --------------------------------------------------------------------------

async def _places(settings: Settings, args: dict, http: httpx.AsyncClient):
    """(there label, there tz, home label, home tz, trip or None)."""
    trip = None
    where = hs.clean(args.get("destination"))
    if not where or hs.clean(args.get("trip")):
        found = ts.trips(settings)
        trip = found[ts.pick(found, args.get("trip"))]
        where = trip["destination"]
    there_label, there = await dates._zone(http, where)
    home_label, home = await dates._zone(http, hs.clean(args.get("home")) or settings.city)
    return there_label, there, ("home" if home_label == "here" else home_label), home, trip


def _gap(there, home, day: date) -> float:
    noon = datetime(day.year, day.month, day.day, 12)
    hours = (noon.replace(tzinfo=there).utcoffset() - noon.replace(tzinfo=home).utcoffset()).total_seconds() / 3600
    return hours - 24 if hours > 12 else hours


def _ahead(label: str, hours: float) -> str:
    if not hours:
        return f"{label} is on the same time as home"
    return f"{label} is {abs(hours):g} hour{'s' if abs(hours) != 1 else ''} {'ahead of' if hours > 0 else 'behind'} home"


def _hhmm(value, default: str) -> datetime:
    text = hs.clean(value) or default
    try:
        return datetime.strptime(text.replace(".", ":"), "%H:%M")
    except ValueError:
        raise ValueError("Give times as HH:MM, e.g. 23:00.") from None


async def jetlag(settings: Settings, args: dict, http: httpx.AsyncClient) -> screen.Shown | str:
    label, there, home_label, home, trip = await _places(settings, args, http)
    fly = hs.parse_day(args.get("day")) if hs.clean(args.get("day")) else (
        date.fromisoformat(trip["start"]) if trip else hs.today())
    hours = _gap(there, home, fly)
    if abs(hours) < 2:
        return f"{_ahead(label, hours)}, so there's no need to shift your sleep."
    n = min(max(int(args.get("days") or 3), 1), 7)
    bed, wake = _hhmm(args.get("bedtime"), "23:00"), _hhmm(args.get("wake"), "07:00")
    east = hours > 0
    tip = ("Get bright light early in the morning; avoid it late evening." if east else
           "Get bright light in the evening; keep mornings dim.")
    rows = []
    for back in range(n, 0, -1):
        shift = timedelta(hours=min(abs(hours), n - back + 1) * (-1 if east else 1))
        day = fly - timedelta(days=back)
        rows.append([f"{day:%a %d %b}", f"{bed + shift:%H:%M}", f"{wake + shift:%H:%M}", tip])
    rows.append([f"{fly:%a %d %b} (arrive)", f"{bed:%H:%M} local", f"{wake:%H:%M} local",
                 "Live on local time from landing; daylight and meals at local times help most."])
    said = (f"{_ahead(label, hours)}. For {n} days before you fly, go to bed and get up an hour "
            f"{'earlier' if east else 'later'} each day; the plan is on the screen.")
    return screen.Shown(said, screen.card(
        "table", f"Jet lag plan: {label}", "travel-jetlag", columns=["Day", "Bed", "Wake", "Tip"], rows=rows,
        text=f"{_ahead(label, hours)}. Times before the flight are {home_label} times."))


async def call_times(settings: Settings, args: dict, http: httpx.AsyncClient) -> screen.Shown:
    label, there, home_label, home, trip = await _places(settings, args, http)
    day = hs.today()
    if trip and date.fromisoformat(trip["start"]) > day:
        day = date.fromisoformat(trip["start"])
    hours = _gap(there, home, day)
    rows, good = [], []
    for h in range(7, 24):
        local = datetime(day.year, day.month, day.day, h, tzinfo=there)
        back = local.astimezone(home)
        ok = h in AWAKE and back.hour in AWAKE
        rows.append([f"{h:02d}:00", f"{back:%H:%M}{' (' + back.strftime('%a') + ')' if back.date() != day else ''}",
                     "good" if ok else ""])
        if ok:
            good.append(h)
    window = f"Good times to call: {good[0]:02d}:00 to {good[-1]:02d}:59 {label} time." if good else \
        "There's no time when you're both usually awake; early morning or late evening is closest."
    return screen.Shown(f"{_ahead(label, hours)}. {window}", screen.card(
        "table", f"Calling home from {label}", "travel-calls", columns=[f"{label} time", f"{home_label} time", "Call?"],
        rows=rows))


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient = None):
    action = args.get("action")
    if action == "phrases":
        return phrases(args)
    if action == "plugs":
        return plugs(args)
    if action == "customs":
        return customs(args)
    if action == "jetlag":
        return await jetlag(settings, args, http)
    if action == "call_times":
        return await call_times(settings, args, http)
    raise ValueError(f"Unknown travel action {action}.")
