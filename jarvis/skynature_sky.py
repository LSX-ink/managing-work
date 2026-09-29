"""Sky watching for the UK: the moon (drawn, dates, monthly calendar), planets tonight, a star map, meteor showers,
eclipses, golden and blue hour, day length, equinoxes and solstices, star facts and an "is the ISS overhead" check.

Everything is worked out on this PC by skynature_astro.py from your home city (JARVIS_CITY, a small built-in UK
table) or a latitude and longitude you give. The only network call is the ISS position (open-notify), which is
sent nothing at all.
"""

import math
from datetime import date, datetime, timedelta

import httpx

import feeds
import screen
import skynature_astro as astro
from config import Settings
from skynature_data import CITIES, CONSTELLATIONS, ECLIPSES, SHOWERS, STAR_FACTS, STARS

screen.EXTRA_KINDS.update({"skynature-moon", "skynature-moon-cal", "skynature-starmap", "skynature-daylight"})

ACTIONS = ["moon", "moon_dates", "moon_calendar", "planets", "star_map", "star_facts", "meteor_showers", "eclipses",
           "golden_hour", "sun_times", "day_length", "seasons", "iss_overhead"]
ISS_RADIUS_KM, ISS_HEIGHT_KM = 6371, 420
BRIGHTNESS = {"Mercury": "bright but always low", "Venus": "dazzling, brightest of all", "Mars": "orange-red",
              "Jupiter": "very bright, creamy white", "Saturn": "steady, yellowish"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def _long(d: date) -> str:
    return f"{d:%A} {d.day} {d:%B}"


def _short(d: date) -> str:
    return f"{d.day} {d:%b}"


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 < n % 100 < 14 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _a(word: str) -> str:
    return ("an " if word[0] in "aeiou" else "a ") + word


def hm(when: datetime | None) -> str:
    return f"{astro.to_local(when):%H:%M}" if when else "none"


def _length(hours: float) -> str:
    total = round(hours * 60)
    return f"{total // 60} hours {total % 60} minutes"


def _day(args: dict, today: date) -> date:
    text = str(args.get("date") or "").strip()
    if not text:
        return today
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("Give the date as year-month-day, like 2026-10-24.") from None


def where(settings: Settings, args: dict) -> tuple[str, float, float]:
    """Name, latitude and longitude: given coordinates, else a city from the small UK table, else London."""
    lat, lon = args.get("latitude"), args.get("longitude")
    if lat is not None and lon is not None:
        if not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
            raise ValueError("Latitude must be between -90 and 90 and longitude between -180 and 180.")
        return "that spot", float(lat), float(lon)
    name = " ".join(str(args.get("city") or settings.city or "").split())
    if not name:
        return "London", *CITIES["london"]
    key = name.lower().split(",")[0].strip()
    found = key if key in CITIES else next((c for c in CITIES if c in name.lower()), None)
    if not found:
        raise ValueError(f"I don't have {name} in my small table of UK cities. Give me a latitude and longitude, "
                         "or name a bigger city nearby.")
    return found.title(), *CITIES[found]


def _card(kind: str, title: str, card_id: str, data: dict, buttons=None) -> dict:
    return screen.card(kind, title, card_id, buttons=buttons, data=data)


# ---- the moon --------------------------------------------------------------------------------

def _moon_when(args: dict, now: datetime) -> tuple[date, datetime]:
    if not args.get("date"):
        return astro.to_local(now).date(), now
    d = _day(args, now.date())
    return d, astro.local_time(d, 21)


def moon(settings: Settings, args: dict, now: datetime) -> screen.Shown:
    d, when = _moon_when(args, now)
    place, lat, lon = where(settings, args)
    ph = astro.moon_phase(when)
    full, new = astro.next_phase(when, "Full moon"), astro.next_phase(when, "New moon")
    events = astro.moon_events(d, lat, lon)
    pct = round(ph["illum"] * 100)
    rows = [["Lit", f"{pct} percent"], ["Age", f"{ph['age']:.1f} days"],
            ["Next full moon", f"{_short(astro.to_local(full).date())} at {hm(full)}"],
            ["Next new moon", f"{_short(astro.to_local(new).date())} at {hm(new)}"],
            ["Moonrise", hm(events["rise"])], ["Moonset", hm(events["set"])]]
    said = (f"The moon on {_long(d)} is a {ph['name'].lower()}, about {pct} percent lit. "
            f"The next full moon is {_long(astro.to_local(full).date())} and the next new moon "
            f"{_long(astro.to_local(new).date())}.")
    data = {"illum": ph["illum"], "waxing": ph["waxing"], "name": ph["name"], "rows": rows, "place": place}
    return screen.Shown(said, _card("skynature-moon", f"Moon {_short(d)}", "skynature-moon", data, buttons=[
        {"label": "Moon calendar", "say": "Show the moon calendar for this month."},
        {"label": "Next phases", "say": "When are the next full and new moons?"}]))


def moon_dates(now: datetime, count: int = 8) -> screen.Shown:
    found = astro.phases_after(now, count)
    rows = [[n, f"{_long(astro.to_local(w).date())}", hm(w)] for w, n in found]
    full = next((w, n) for w, n in found if n == "Full moon")
    new = next((w, n) for w, n in found if n == "New moon")
    said = (f"The next full moon is {_long(astro.to_local(full[0]).date())} at {hm(full[0])}, "
            f"and the next new moon is {_long(astro.to_local(new[0]).date())}.")
    return screen.Shown(said, screen.card("table", "Moon phases", "skynature-phases",
                                          columns=["Phase", "Date", "Time"], rows=rows,
                                          buttons=[{"label": "Moon tonight", "say": "What's the moon tonight?"}]))


def moon_calendar(args: dict, today: date) -> screen.Shown:
    month, year = int(args.get("month") or today.month), int(args.get("year") or today.year)
    if not 1 <= month <= 12 or not 1900 <= year <= 2200:
        raise ValueError("Which month, 1 to 12?")
    first = date(year, month, 1)
    length = ((date(year + (month == 12), month % 12 + 1, 1)) - first).days
    tags, spoken = {}, []
    short = {"New moon": "New", "Full moon": "Full", "First quarter": "1st Q", "Last quarter": "Last Q"}
    for when, name in astro.phases_after(astro.local_time(first) - timedelta(days=1), 12):
        local = astro.to_local(when).date()
        if local.year == year and local.month == month:
            tags[local.day] = short[name]
            spoken.append(f"{name.lower()} on the {_ordinal(local.day)}")
    days = []
    for n in range(1, length + 1):
        ph = astro.moon_phase(astro.local_time(date(year, month, n), 21))
        days.append({"d": n, "illum": round(ph["illum"], 3), "waxing": ph["waxing"], "tag": tags.get(n, "")})
    prev_m, next_m = (first - timedelta(days=1)), (first + timedelta(days=32))
    said = f"Here is the moon in {MONTHS[month - 1]} {year}: " + ", ".join(spoken) + "."
    data = {"month": MONTHS[month - 1], "year": year, "offset": first.weekday(), "days": days}
    return screen.Shown(said, _card("skynature-moon-cal", f"Moon {MONTHS[month - 1]} {year}", "skynature-moon-cal", data,
                                    buttons=[{"label": f"< {MONTHS[prev_m.month - 1]}",
                                              "say": f"Show the moon calendar for {MONTHS[prev_m.month - 1]} {prev_m.year}."},
                                             {"label": f"{MONTHS[next_m.month - 1]} >",
                                              "say": f"Show the moon calendar for {MONTHS[next_m.month - 1]} {next_m.year}."}]))


# ---- planets and the star map ------------------------------------------------------------------

def _height(alt: float) -> str:
    return "low" if alt < 20 else "well up" if alt < 45 else "high"


def _dark_times(d: date, lat: float, lon: float) -> list[datetime]:
    """Every 20 minutes between 5pm and 7am when the sun is well below the horizon (UTC)."""
    start = astro.local_time(d, 17)
    times = [start + timedelta(minutes=20 * i) for i in range(int(14 * 3))]
    return [t for t in times if astro.sun_alt_az(t, lat, lon)[0] < -4]


def _period(first: datetime, last: datetime, dark: list[datetime]) -> str:
    """Whether a planet's window is the evening, before dawn or all night, within the dark hours."""
    near = timedelta(minutes=60)
    early, late = first - dark[0] < near, dark[-1] - last < near
    return "all night" if early and late else "evening" if early else "before dawn" if late else "late evening"


def planets(settings: Settings, args: dict, now: datetime) -> screen.Shown:
    d = _day(args, astro.to_local(now).date())
    place, lat, lon = where(settings, args)
    dark = _dark_times(d, lat, lon)
    rows, seen = [], []
    for name in astro.PLANETS:
        up = [(t, *astro.planet_alt_az(name, t, lat, lon)) for t in dark]
        up = [x for x in up if x[1] >= 6]
        if not up:
            continue
        best = max(up, key=lambda x: x[1])
        window = f"{_period(up[0][0], up[-1][0], dark)} {hm(up[0][0])} to {hm(up[-1][0])}"
        rows.append([name, window, f"{astro.compass(best[2])}, {_height(best[1])} ({best[1]:.0f} degrees)", BRIGHTNESS[name]])
        seen.append(f"{name} in the {astro.compass(best[2])}, {_height(best[1])} ({_period(up[0][0], up[-1][0], dark)})")
    if not rows:
        said = f"None of the five bright planets is properly visible from {place} on {_long(d)}."
        return screen.Shown(said, screen.card("text", "Planets tonight", "skynature-planets", text=said))
    said = f"Planets you can see from {place} on {_long(d)}: " + "; ".join(seen) + "."
    return screen.Shown(said, screen.card(
        "table", f"Planets {_short(d)}", "skynature-planets", columns=["Planet", "Visible", "Where", "Looks"], rows=rows,
        buttons=[{"label": "Star map", "say": "Show me the star map for tonight."},
                 {"label": "Moon", "say": "What's the moon tonight?"}]))


def _project(alt: float, az: float) -> tuple[float, float]:
    r = (90 - alt) / 90
    return round(-r * math.sin(math.radians(az)), 3), round(-r * math.cos(math.radians(az)), 3)


def star_map(settings: Settings, args: dict, now: datetime) -> screen.Shown:
    d = _day(args, astro.to_local(now).date())
    place, lat, lon = where(settings, args)
    hour = float(args.get("hour", 22))
    if not 0 <= hour < 24:
        raise ValueError("Give the hour as 0 to 23.")
    when = astro.local_time(d if hour >= 12 else d + timedelta(days=1), hour)
    j = astro.jd(when)
    pos = {n: astro.alt_az(ra * 15, dec, j, lat, lon) for n, (ra, dec, _) in STARS.items()}
    stars = [[*_project(alt, az), STARS[n][2], n if STARS[n][2] < 1.6 else ""] for n, (alt, az) in pos.items() if alt > 0]
    lines, labels, names = [], [], []
    for cname, (members, pairs) in CONSTELLATIONS.items():
        up = [m for m in members if pos[m][0] > 0]
        if not up:
            continue
        lines += [[*_project(*pos[a]), *_project(*pos[b])] for a, b in pairs if pos[a][0] > 0 and pos[b][0] > 0]
        pts = [_project(*pos[m]) for m in up]
        short = cname.split(" (")[0]
        labels.append([short, round(sum(p[0] for p in pts) / len(pts), 3), round(sum(p[1] for p in pts) / len(pts), 3)])
        if max(pos[m][0] for m in up) > 15:
            names.append((min(STARS[m][2] for m in up), short))
    marks = []
    for p in astro.PLANETS:
        alt, az = astro.planet_alt_az(p, when, lat, lon)
        if alt > 3:
            marks.append({"name": p, "x": _project(alt, az)[0], "y": _project(alt, az)[1]})
    m_alt, m_az = astro.moon_alt_az(when, lat, lon)
    ph = astro.moon_phase(when)
    moon_mark = ({"x": _project(m_alt, m_az)[0], "y": _project(m_alt, m_az)[1], "illum": ph["illum"], "waxing": ph["waxing"]}
                 if m_alt > 0 else None)
    lit = astro.sun_alt_az(when, lat, lon)[0] > -12
    top = ", ".join(n for _, n in sorted(names)[:6]) or "few of my bright stars"
    said = (f"Here is the sky over {place} at {astro.to_local(when):%H:%M} on {_long(astro.to_local(when).date())}. "
            f"Look for {top}." + (" It is still twilight, so only the brightest will show." if lit else ""))
    data = {"stars": stars, "lines": lines, "labels": labels, "planets": marks, "moon": moon_mark, "twilight": lit,
            "when": f"{astro.to_local(when):%a %d %b %H:%M}", "place": place}
    return screen.Shown(said, _card("skynature-starmap", f"Star map {_short(astro.to_local(when).date())}",
                                    "skynature-starmap", data, buttons=[
        {"label": "Planets tonight", "say": "Which planets can I see tonight?"},
        {"label": "Star facts", "say": "Tell me some facts about the bright stars."}]))


def star_facts(name: str) -> screen.Shown:
    name = " ".join(str(name or "").split())
    if not name:
        items = [{"label": f"{n} ({c}, {colour})", "say": f"Tell me about the star {n}."}
                 for n, (c, colour, _, _) in STAR_FACTS.items()]
        return screen.Shown("Here are some bright stars to ask about.",
                            screen.card("list", "Bright stars", "skynature-stars", items=items))
    found = next((n for n in STAR_FACTS if n.lower() == name.lower()), None) or \
        next((n for n in STAR_FACTS if name.lower() in n.lower()), None)
    if not found:
        raise ValueError(f"I don't have facts on {name}. Try Polaris, Sirius, Betelgeuse, Vega or Arcturus.")
    con, colour, ly, fact = STAR_FACTS[found]
    said = f"{found} is a {colour} star in {con}, about {ly:g} light years away. {fact}"
    return screen.Shown(said, screen.card("text", found, "skynature-star", text=said, buttons=[
        {"label": "Star map", "say": "Show me the star map for tonight."}]))


# ---- showers and eclipses ------------------------------------------------------------------

def _moon_verdict(illum: float) -> str:
    return "dark sky, good" if illum < 0.35 else "moonlit, so-so" if illum < 0.7 else "bright moon, poor"


def meteor_showers(args: dict, today: date) -> screen.Shown:
    upcoming = []
    for name, active, (m, day), rate, best, source in SHOWERS:
        peak = date(today.year, m, day)
        if peak < today:
            peak = date(today.year + 1, m, day)
        upcoming.append((peak, name, active, rate, best, source))
    upcoming.sort()
    q = str(args.get("name") or "").strip().lower()
    if q:
        upcoming = [u for u in upcoming if q in u[1].lower()]
        if not upcoming:
            raise ValueError("I know the Quadrantids, Lyrids, Eta Aquariids, Perseids, Draconids, Orionids, Taurids, "
                             "Leonids, Geminids and Ursids.")
    rows = []
    for peak, name, active, rate, best, source in upcoming:
        illum = astro.moon_phase(astro.local_time(peak, 1))["illum"]
        rows.append([name, _short(peak), f"about {rate} an hour", _moon_verdict(illum), best])
    peak, name, active, rate, best, source = upcoming[0]
    illum = astro.moon_phase(astro.local_time(peak, 1))["illum"]
    days = (peak - today).days
    said = (f"Next up are the {name}, peaking around {_long(peak)}, "
            f"{'tonight' if days == 0 else f'in {days} days'}, up to about {rate} an hour with {_moon_verdict(illum)} "
            f"moon conditions. Best {best}. Peak dates can shift by a day.")
    return screen.Shown(said, screen.card("table", "Meteor showers", "skynature-showers",
                                          columns=["Shower", "Peak", "Rate (ideal sky)", "Moon at peak", "Best"], rows=rows))


def _seen(e: tuple) -> bool:
    """Worth going out for from the UK: not a faint penumbral shading and not out of sight."""
    return e[2] != "penumbral" and not e[4].startswith("Not")


def eclipses(args: dict, today: date) -> screen.Shown:
    year = args.get("year")
    found = [e for e in ECLIPSES if (int(year) == int(e[0][:4]) if year else e[0] >= today.isoformat())]
    if args.get("visible_only"):
        found = [e for e in found if _seen(e)]
    if not found:
        raise ValueError("I have eclipses for 2026 to 2030 only.")
    rows = [[_short(date.fromisoformat(e[0])) + f" {e[0][:4]}", f"{e[2]} {e[1]}", e[3], e[4]] for e in found]
    first = found[0]
    nxt = next((e for e in found if _seen(e)), None)
    said = f"The next is {_a(first[2])} {first[1]} eclipse on {_long(date.fromisoformat(first[0]))} {first[0][:4]}. {first[4]}"
    if nxt and nxt is not first:
        said += (f" The next you can properly see from the UK is {_a(nxt[2])} {nxt[1]} eclipse on "
                 f"{_long(date.fromisoformat(nxt[0]))} {nxt[0][:4]}.")
    return screen.Shown(said, screen.card(
        "table", "Eclipses", "skynature-eclipses", columns=["Date", "Kind", "Seen from", "In the UK"], rows=rows,
        buttons=[{"label": "UK-visible only", "say": "Which eclipses can I actually see from the UK?"}]))


# ---- sun: golden hour, day length, seasons ----------------------------------------------------

def _bands(d: date, lat: float, lon: float) -> list[list]:
    """The local day as runs of night, blue, golden and day, each [start minute, end minute, kind]."""
    out = []
    for i in range(0, 1440, 10):
        alt = astro.sun_alt_az(astro.local_time(d, i / 60), lat, lon)[0]
        kind = "night" if alt < -8 else "blue" if alt < -4 else "golden" if alt < 6 else "day"
        if out and out[-1][2] == kind:
            out[-1][1] = i + 10
        else:
            out.append([i, i + 10, kind])
    return out


def _sun_rows(d: date, lat: float, lon: float) -> tuple[dict, list]:
    ev = {t: astro.sun_events(d, lat, lon, alt) for t, alt in (
        ("sun", astro.SUN_RISE), ("golden", 6), ("blue_in", -4), ("blue_out", -8), ("civil", -6), ("dark", -18))}
    length = astro.daylight_hours(d, lat, lon)
    change = (astro.daylight_hours(d + timedelta(days=1), lat, lon) - length) * 60
    rows = [["Sunrise", hm(ev["sun"]["rise"])], ["Sunset", hm(ev["sun"]["set"])],
            ["Daylight", f"{_length(length)} ({change:+.0f} min a day)"],
            ["Morning golden hour", f"{hm(ev['blue_in']['rise'])} to {hm(ev['golden']['rise'])}"],
            ["Evening golden hour", f"{hm(ev['golden']['set'])} to {hm(ev['blue_in']['set'])}"],
            ["Morning blue hour", f"{hm(ev['blue_out']['rise'])} to {hm(ev['blue_in']['rise'])}"],
            ["Evening blue hour", f"{hm(ev['blue_in']['set'])} to {hm(ev['blue_out']['set'])}"],
            ["Civil twilight", f"{hm(ev['civil']['rise'])} to {hm(ev['civil']['set'])}"],
            ["Fully dark", f"{hm(ev['dark']['set'])} to {hm(ev['dark']['rise'])}" if ev["dark"]["set"] else "not dark this time of year"]]
    return ev, rows


def _daylight_card(d: date, place: str, lat: float, lon: float, rows: list, ev: dict) -> dict:
    marks = [{"min": round((astro.to_local(w) - datetime.combine(d, datetime.min.time())).total_seconds() / 60),
              "label": label} for label, w in (("rise", ev["sun"]["rise"]), ("set", ev["sun"]["set"])) if w]
    data = {"bands": _bands(d, lat, lon), "marks": marks, "rows": rows, "place": place, "date": _long(d)}
    return _card("skynature-daylight", f"Light in {place} {_short(d)}", "skynature-daylight", data, buttons=[
        {"label": "Day length chart", "say": "Show me a chart of day length through the year."}])


def golden_hour(settings: Settings, args: dict, now: datetime) -> screen.Shown:
    d = _day(args, astro.to_local(now).date())
    place, lat, lon = where(settings, args)
    ev, rows = _sun_rows(d, lat, lon)
    eve = f"{hm(ev['golden']['set'])} to {hm(ev['blue_in']['set'])}"
    morn = f"{hm(ev['blue_in']['rise'])} to {hm(ev['golden']['rise'])}"
    said = (f"In {place} on {_long(d)}, golden hour is {morn} in the morning and {eve} in the evening. "
            f"Blue hour follows the evening one, until {hm(ev['blue_out']['set'])}.")
    return screen.Shown(said, _daylight_card(d, place, lat, lon, rows, ev))


def sun_times(settings: Settings, args: dict, now: datetime) -> screen.Shown:
    d = _day(args, astro.to_local(now).date())
    place, lat, lon = where(settings, args)
    ev, rows = _sun_rows(d, lat, lon)
    length = astro.daylight_hours(d, lat, lon)
    change = (astro.daylight_hours(d + timedelta(days=1), lat, lon) - length) * 60
    said = (f"In {place} on {_long(d)}: sunrise {hm(ev['sun']['rise'])}, sunset {hm(ev['sun']['set'])}, "
            f"{_length(length)} of daylight, which is {abs(change):.0f} minutes {'longer' if change > 0 else 'shorter'} "
            "tomorrow.")
    return screen.Shown(said, _daylight_card(d, place, lat, lon, rows, ev))


def day_length(settings: Settings, args: dict, today: date) -> screen.Shown:
    year = int(args.get("year") or today.year)
    place, lat, lon = where(settings, args)
    days = [date(year, 1, 1) + timedelta(days=i) for i in range(365 + (year % 4 == 0 and (year % 100 or year % 400 == 0)))]
    hours = {d: astro.daylight_hours(d, lat, lon) for d in days}
    longest, shortest = max(hours, key=hours.get), min(hours, key=hours.get)
    sample = days[::14]
    said = (f"In {place} the longest day is {_short(longest)} with {_length(hours[longest])} of daylight, and the "
            f"shortest is {_short(shortest)} with {_length(hours[shortest])}.")
    return screen.Shown(said, screen.card(
        "chart", f"Daylight in {place} {year}", "skynature-daylength",
        chart={"type": "line", "labels": [_short(d) for d in sample], "values": [round(hours[d], 2) for d in sample],
               "unit": "h"}, buttons=[{"label": "Today's times", "say": "When are sunrise and sunset today?"}]))


def seasons(args: dict, today: date) -> screen.Shown:
    year = int(args.get("year") or today.year)
    found = astro.season_starts(year)
    rows = [[n, _long(astro.to_local(w).date()), hm(w)] for n, w in found]
    ahead = next(((n, w) for n, w in found if astro.to_local(w).date() >= today), None)
    said = (f"The next one is the {ahead[0]}, on {_long(astro.to_local(ahead[1]).date())} at {hm(ahead[1])}."
            if ahead else f"All four of {year}'s equinoxes and solstices are past.")
    return screen.Shown(said, screen.card("table", f"Equinoxes and solstices {year}", "skynature-seasons",
                                          columns=["Moment", "Date", "UK time"], rows=rows))


# ---- ISS -------------------------------------------------------------------------------------

def _iss_view(lat: float, lon: float, iss_lat: float, iss_lon: float) -> tuple[float, float]:
    """Ground distance in km to the point under the ISS, and its elevation angle in degrees (negative: below)."""
    a, b = math.radians(lat), math.radians(iss_lat)
    gamma = math.acos(min(1.0, max(-1.0, math.sin(a) * math.sin(b)
                                    + math.cos(a) * math.cos(b) * math.cos(math.radians(iss_lon - lon)))))
    ratio = ISS_RADIUS_KM / (ISS_RADIUS_KM + ISS_HEIGHT_KM)
    return ISS_RADIUS_KM * gamma, math.degrees(math.atan2(math.cos(gamma) - ratio, math.sin(gamma)))


async def iss_overhead(http: httpx.AsyncClient, settings: Settings, args: dict) -> screen.Shown:
    place, lat, lon = where(settings, args)
    body = await feeds.fetch_json(http, feeds.ISS_NOW, "space station tracker")
    try:
        iss_lat, iss_lon = float(body["iss_position"]["latitude"]), float(body["iss_position"]["longitude"])
    except (KeyError, TypeError, ValueError):
        raise feeds._fail("space station tracker") from None
    km, elev = _iss_view(lat, lon, iss_lat, iss_lon)
    over = feeds.region(iss_lat, iss_lon)
    if elev >= 60:
        verdict = f"Yes, it's almost overhead of {place} right now, {elev:.0f} degrees up."
    elif elev > 0:
        verdict = (f"It's above the horizon of {place}, {elev:.0f} degrees up, but you only see it if it is dusk or dawn "
                   "and the sky is clear.")
    else:
        verdict = f"No, it's below the horizon of {place}, about {km:,.0f} km away."
    said = f"{verdict} The space station is over {over} at the moment."
    rows = [["From " + place, f"{km:,.0f} km along the ground"], ["Height in your sky", f"{elev:.0f} degrees" if elev > 0 else "below the horizon"],
            ["Over", over]]
    return screen.Shown(said, screen.card("table", "Is the ISS overhead?", "skynature-iss", columns=["", "Now"], rows=rows,
                                          buttons=[{"label": "Check again", "say": "Is the ISS overhead now?"}]))


# ---- the tool ----------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "sky_watch",
        "description": "Sky watching for the UK, worked out locally. action: moon = phase drawn on screen with "
                       "illumination, moonrise and next full and new moon (date optional); moon_dates = next full, new "
                       "and quarter moons; moon_calendar = a month of moon phases (month, year); planets = which bright "
                       "planets are visible tonight and where; star_map = sky chart of tonight's constellations (hour "
                       "0 to 23, default 22); star_facts = facts on a bright star by name (blank lists them); "
                       "meteor_showers = the year's showers with peak dates and moon conditions (name optional); "
                       "eclipses = solar and lunar eclipses 2026 to 2030 (year, visible_only); golden_hour = golden "
                       "and blue hour times with a daylight bar; sun_times = sunrise, sunset, daylight length and "
                       "darkness; day_length = chart of daylight through the year; seasons = equinox and solstice "
                       "dates; iss_overhead = is the space station overhead now. Place is the home city unless city "
                       "or latitude and longitude are given. Dates are YYYY-MM-DD.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "date": {"type": "string", "description": "YYYY-MM-DD; default today."},
                "month": {"type": "integer", "description": "moon_calendar: 1 to 12."},
                "year": {"type": "integer"},
                "hour": {"type": "number", "description": "star_map: clock hour 0 to 23; default 22 (10pm)."},
                "name": {"type": "string", "description": "star_facts: a star. meteor_showers: a shower."},
                "city": {"type": "string", "description": "A UK city; default the home city."},
                "latitude": {"type": "number"}, "longitude": {"type": "number"},
                "visible_only": {"type": "boolean", "description": "eclipses: only those visible from the UK."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"sky_watch"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient, now: datetime | None = None):
    now = now or datetime.now(astro.UTC)
    action = args.get("action")
    today = astro.to_local(now).date()
    if action == "moon":
        return moon(settings, args, now)
    if action == "moon_dates":
        return moon_dates(now)
    if action == "moon_calendar":
        return moon_calendar(args, today)
    if action == "planets":
        return planets(settings, args, now)
    if action == "star_map":
        return star_map(settings, args, now)
    if action == "star_facts":
        return star_facts(args.get("name"))
    if action == "meteor_showers":
        return meteor_showers(args, today)
    if action == "eclipses":
        return eclipses(args, today)
    if action == "golden_hour":
        return golden_hour(settings, args, now)
    if action == "sun_times":
        return sun_times(settings, args, now)
    if action == "day_length":
        return day_length(settings, args, today)
    if action == "seasons":
        return seasons(args, today)
    if action == "iss_overhead":
        return await iss_overhead(http, settings, args)
    raise ValueError(f"Unknown sky action: {action}")
