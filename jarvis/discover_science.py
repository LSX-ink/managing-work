"""Discover: the periodic table, planets and moons, constellations over the UK, tonight's sky,
a science fact and unit of the day, and two countries side by side.

Everything is local data except sunset (Open-Meteo, via dates.sun) and countries (restcountries.com, keyless);
only a city or country name is sent.
"""

import math
from datetime import date, datetime, timezone
from urllib.parse import quote

import httpx

import dates
import screen
from config import Settings
from discover_data import BY_MONTH, CIRCUMPOLAR, CONSTELLATIONS, ELEMENTS, MOONS, PLANET_COLUMNS, PLANETS, \
    SCIENCE_FACTS, UNITS

screen.EXTRA_KINDS.add("discover-periodic")

COUNTRIES_URL = "https://restcountries.com/v3.1/name/"
COUNTRY_FIELDS = "name,capital,population,area,currencies,languages,region,flag"
ALIASES = {"aluminum": "aluminium", "cesium": "caesium", "sulphur": "sulfur"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
# Orbital elements at J2000 (NASA JPL "Approximate positions of the planets"):
# a (AU), e, mean longitude L (deg), its rate per century, longitude of perihelion (deg).
ORBITS = {
    "Mercury": (0.38709927, 0.20563593, 252.25032350, 149472.67411175, 77.45779628),
    "Venus": (0.72333566, 0.00677672, 181.97909950, 58517.81538729, 131.60246718),
    "Earth": (1.00000261, 0.01671123, 100.46457166, 35999.37244981, 102.93768193),
    "Mars": (1.52371034, 0.09339410, -4.55343205, 19140.30268499, -23.94362959),
    "Jupiter": (5.20288700, 0.04838624, 34.39644051, 3034.74612775, 14.72847983),
    "Saturn": (9.53667594, 0.05386179, 49.95424423, 1222.49362201, 92.59887831),
}
# Degrees from the Sun a planet needs to be to show in a dark sky.
MIN_ELONGATION = {"Mercury": 18, "Venus": 10, "Mars": 15, "Jupiter": 15, "Saturn": 15}


def _key(text) -> str:
    return " ".join(str(text or "").lower().split())


# ---- Elements ---------------------------------------------------------------------------------

def find_element(query) -> dict:
    q = _key(query)
    q = ALIASES.get(q, q)
    for e in ELEMENTS:
        if q in (e["name"].lower(), e["symbol"].lower(), str(e["number"])):
            return e
    near = [e for e in ELEMENTS if q and q in e["name"].lower()]
    if near:
        return near[0]
    raise ValueError(f"I don't know an element called {query}. Try a name, symbol or number from 1 to 118.")


def _block(e: dict) -> str:
    if e["group"] == 0:
        return "f"
    if e["group"] in (1, 2) or e["number"] == 2:
        return "s"
    return "d" if 3 <= e["group"] <= 12 else "p"


def element(query) -> screen.Shown:
    e = find_element(query)
    where = f"group {e['group']}, period {e['period']}" if e["group"] else f"period {e['period']}, the f-block"
    mass = e["mass"].strip("[]") + (" (most stable isotope)" if e["mass"].startswith("[") else "")
    said = (f"{e['name']}, symbol {e['symbol']}, is element {e['number']}: a {e['category']} in {where}, "
            f"with an atomic mass of {mass}.")
    rows = [["Symbol", e["symbol"]], ["Atomic number", e["number"]], ["Atomic mass", mass],
            ["Group", e["group"] or "f-block"], ["Period", e["period"]], ["Block", _block(e)],
            ["Category", e["category"]]]
    buttons = [{"label": "Periodic table", "say": f"Show me the periodic table with {e['name']} highlighted."}]
    for n in (e["number"] - 1, e["number"] + 1):
        if 1 <= n <= 118:
            other = ELEMENTS[n - 1]
            buttons.append({"label": other["name"], "say": f"Tell me about the element {other['name']}."})
    return screen.Shown(said, screen.card("table", f"{e['number']} {e['name']}", "discover-element",
                                          buttons=buttons, columns=["", e["name"]], rows=rows))


def periodic_table(highlight="") -> screen.Shown:
    mark = find_element(highlight)["number"] if highlight else 0
    cells = [[e["number"], e["symbol"], e["name"], e["group"], e["period"], e["category"]] for e in ELEMENTS]
    return screen.Shown("The periodic table is on the screen; click any element to hear about it.",
                        screen.card("discover-periodic", "Periodic table", "discover-periodic",
                                    data={"elements": cells, "highlight": mark}))


# ---- Planets, moons, stars --------------------------------------------------------------------

def planet(query) -> screen.Shown:
    q = _key(query).removeprefix("the ")
    if q in ("moon", "earth's moon", "our moon"):
        q = "moon"
    name = next((p for p in PLANETS if p.lower() == q), None)
    if name:
        kind, dia, dist, day, year, moons, g, temp, fact = PLANETS[name]
        said = (f"{name} is a {kind} planet {dia:,} km across, {dist:g} million km from the Sun. A year there is "
                f"{year:g} Earth days and it has {moons} known moons. {fact}")
        rows = [[c, v] for c, v in zip(PLANET_COLUMNS[1:], _planet_row(name)[1:])]
        buttons = [{"label": "Compare planets", "say": "Compare all the planets in a table."}]
        buttons += [{"label": m, "say": f"Tell me about {m}, the moon of {name}."}
                    for m, info in MOONS.items() if info[0] == name][:4]
        return screen.Shown(said, screen.card("table", name, "discover-planet", buttons=buttons,
                                              columns=["", name], rows=rows))
    moon = next((m for m in MOONS if m.lower() == q), None)
    if moon:
        host, dia, fact = MOONS[moon]
        said = f"{'The Moon' if moon == 'Moon' else moon} orbits {host} and is {dia:,} km across. {fact}"
        return screen.Shown(said, screen.card("text", moon, "discover-planet", text=said,
                                              buttons=[{"label": host, "say": f"Tell me about the planet {host}."}]))
    if q == "pluto":
        said = "Pluto is a dwarf planet 2,377 km across, out in the Kuiper belt. A year there is 248 Earth years."
        return screen.Shown(said, screen.card("text", "Pluto", "discover-planet", text=said, buttons=[
            {"label": "Charon", "say": "Tell me about Charon, the moon of Pluto."}]))
    raise ValueError(f"I don't have facts on {query}. Try a planet like Mars or a moon like Europa.")


def _planet_row(name: str) -> list:
    kind, dia, dist, day, year, moons, g, temp, _ = PLANETS[name]
    return [name, kind, f"{dia:,}", f"{dist:g}", f"{day:g}", f"{year:g}", moons, g, temp]


def compare_planets() -> screen.Shown:
    return screen.Shown("Here are the eight planets side by side. Jupiter is the biggest and Mercury the smallest.",
                        screen.card("table", "The planets", "discover-planets", columns=PLANET_COLUMNS,
                                    rows=[_planet_row(p) for p in PLANETS]))


def constellations(month, name="") -> screen.Shown:
    if name:
        found = next((c for c in CONSTELLATIONS if _key(c) == _key(name).replace("ö", "o")), None)
        if not found:
            raise ValueError(f"I don't have tips for {name}.")
        return screen.Shown(f"{found}: {CONSTELLATIONS[found]}",
                            screen.card("text", found, "discover-constellation", text=CONSTELLATIONS[found]))
    month = int(month)
    if not 1 <= month <= 12:
        raise ValueError("Which month, 1 to 12?")
    items = [{"label": f"{c}: {CONSTELLATIONS[c]}", "say": f"Tell me about the constellation {c}."}
             for c in BY_MONTH[month]]
    items += [{"label": f"{c} (all year): {CONSTELLATIONS[c]}", "say": f"Tell me about the constellation {c}."}
              for c in CIRCUMPOLAR]
    said = (f"In {MONTHS[month - 1]} evenings from the UK look for {', '.join(BY_MONTH[month][:-1])} and "
            f"{BY_MONTH[month][-1]}, plus the Plough and Cassiopeia all year.")
    return screen.Shown(said, screen.card("list", f"Stars in {MONTHS[month - 1]}", "discover-stars", items=items))


def _heliocentric(name: str, centuries: float) -> tuple[float, float]:
    a, e, L0, rate, peri = ORBITS[name]
    mean = math.radians((L0 + rate * centuries - peri) % 360)
    ecc = mean
    for _ in range(8):
        ecc -= (ecc - e * math.sin(ecc) - mean) / (1 - e * math.cos(ecc))
    x, y = a * (math.cos(ecc) - e), a * math.sqrt(1 - e * e) * math.sin(ecc)
    w = math.radians(peri)
    return x * math.cos(w) - y * math.sin(w), x * math.sin(w) + y * math.cos(w)


def elongation(name: str, when: datetime) -> float:
    """Degrees between a planet and the Sun as seen from Earth; positive = east of the Sun (evening sky)."""
    t = (when - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).total_seconds() / 86400 / 36525
    ex, ey = _heliocentric("Earth", t)
    px, py = _heliocentric(name, t)
    sun = math.degrees(math.atan2(-ey, -ex))
    body = math.degrees(math.atan2(py - ey, px - ex))
    return (body - sun + 180) % 360 - 180


def visible_planets(d: date) -> list[tuple[str, str]]:
    when = datetime(d.year, d.month, d.day, 21, tzinfo=timezone.utc)
    out = []
    for name, least in MIN_ELONGATION.items():
        angle = elongation(name, when)
        if abs(angle) >= least:
            out.append((name, "evening" if angle > 0 else "morning" if abs(angle) < 150 else "all night"))
    return out


async def night_sky(http: httpx.AsyncClient, city: str, d: date) -> screen.Shown:
    try:
        sun = await dates.sun(http, city, d) if city else "Sunset time needs a home city (JARVIS_CITY)."
    except (httpx.HTTPError, ValueError, KeyError):
        sun = "I couldn't get the sunset time just now."
    moon = dates.moon(d)
    planets = visible_planets(d)
    seen = "; ".join(f"{p} ({when})" for p, when in planets) or "none of the bright planets"
    said = f"{sun} {moon} Planets to look for: {seen}."
    rows = [["Sun", sun], ["Moon", moon.split(" is ", 1)[-1].rstrip(".")],
            *[[p, f"visible in the {when} sky" if when != "all night" else "up all night"] for p, when in planets]]
    return screen.Shown(said, screen.card(
        "table", f"Night sky {d:%d %b}", "discover-night", columns=["", "Tonight"], rows=rows,
        buttons=[{"label": "Constellations", "say": "What constellations can I see this month?"}]))


def fact_of_day(d: date) -> screen.Shown:
    fact = SCIENCE_FACTS[d.toordinal() % len(SCIENCE_FACTS)]
    unit, measures, what = UNITS[(d.toordinal() * 7) % len(UNITS)]
    said = f"Science fact of the day: {fact} Unit of the day: the {unit}, for {measures}: {what}."
    text = f"{fact}\n\nUnit of the day: the {unit} ({measures})\n{what[0].upper()}{what[1:]}."
    return screen.Shown(said, screen.card("text", f"Science for {d:%d %B}", "discover-daily", text=text))


# ---- Countries ----------------------------------------------------------------------------------

async def _country(http: httpx.AsyncClient, name: str) -> dict:
    name = " ".join(str(name or "").split())[:60]
    if not name:
        raise ValueError("Which two countries?")
    try:
        r = await http.get(COUNTRIES_URL + quote(name), params={"fields": COUNTRY_FIELDS}, timeout=10)
    except httpx.HTTPError:
        raise ValueError("The countries service isn't answering right now.") from None
    if r.status_code == 404:
        raise ValueError(f"I couldn't find a country called {name}.")
    if r.status_code >= 400:
        raise ValueError("The countries service isn't answering right now.")
    found = r.json()
    exact = [c for c in found if c.get("name", {}).get("common", "").lower() == name.lower()]
    return (exact or found)[0]


def _values(c: dict) -> list[str]:
    pop, area = c.get("population") or 0, c.get("area") or 0
    money = ", ".join(f"{v.get('name')} ({k})" for k, v in (c.get("currencies") or {}).items())
    return [c.get("flag", ""), ", ".join(c.get("capital") or []) or "none", f"{pop:,}", f"{area:,.0f} km²",
            f"{pop / area:,.0f} per km²" if area else "?", money or "?",
            ", ".join((c.get("languages") or {}).values()) or "?", c.get("region", "?")]


async def compare_countries(http: httpx.AsyncClient, first: str, second: str) -> screen.Shown:
    a, b = await _country(http, first), await _country(http, second)
    na, nb = a["name"]["common"], b["name"]["common"]
    va, vb = _values(a), _values(b)
    labels = ["Flag", "Capital", "Population", "Area", "People per km²", "Currency", "Languages", "Region"]
    bigger = na if (a.get("population") or 0) >= (b.get("population") or 0) else nb
    said = f"{na} has {va[2]} people and {nb} has {vb[2]}, so {bigger} is more populous. The table is on screen."
    return screen.Shown(said, screen.card("table", f"{na} vs {nb}", "discover-countries", columns=["", na, nb],
                                          rows=[[l, x, y] for l, x, y in zip(labels, va, vb)]))


ACTIONS = ["element", "periodic_table", "planet", "compare_planets", "constellations", "night_sky", "fact_of_day",
           "compare_countries"]


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "science_and_space",
        "description": "Science, space and world facts with pop-ups. element: facts on a chemical element by name, "
                       "symbol or number; periodic_table: show the periodic table (optionally highlight an element); "
                       "planet: facts on a planet or moon; compare_planets: table of all planets; constellations: "
                       "stars visible from the UK this month (or month 1-12), or tips for one constellation by name; "
                       "night_sky: tonight's sunset, moon phase and visible planets; fact_of_day: science fact and "
                       "unit of the day; compare_countries: two countries side by side (population, area, capital, "
                       "currency, languages).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "Element, planet, moon or constellation."},
                "month": {"type": "integer", "description": "1 to 12; default this month."},
                "city": {"type": "string", "description": "night_sky: default the home city."},
                "country": text, "country2": text,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"science_and_space"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient, today: date | None = None):
    today = today or date.today()
    action, what = args.get("action"), args.get("name") or ""
    if action == "element":
        return element(what)
    if action == "periodic_table":
        return periodic_table(what)
    if action == "planet":
        return planet(what)
    if action == "compare_planets":
        return compare_planets()
    if action == "constellations":
        return constellations(args.get("month") or today.month, what)
    if action == "night_sky":
        return await night_sky(http, args.get("city") or settings.city, today)
    if action == "fact_of_day":
        return fact_of_day(today)
    if action == "compare_countries":
        return await compare_countries(http, args.get("country"), args.get("country2"))
    raise ValueError(f"Unknown science action: {action}")
