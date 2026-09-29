"""A small built-in ephemeris for the sky-and-nature abilities: sun, moon, phases, planets and star positions.

Low-precision formulas (Astronomical Almanac / Meeus), good to a few minutes and a degree or so, which is plenty
for "when is golden hour" and "where is Jupiter". Times are UTC datetimes; UK local time is worked out here too
(GMT, or BST between the last Sundays of March and October), so no time zone database is needed.
"""

import math
from datetime import date, datetime, timedelta, timezone

from discover_science import MIN_ELONGATION, _heliocentric

UTC = timezone.utc
J2000 = datetime(2000, 1, 1, 12, tzinfo=UTC)
SYNODIC = 29.530588861
SUN_RISE = -0.833  # centre of the sun below the horizon at sunrise and sunset
MOON_RISE = 0.125
COMPASS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]
PLANETS = list(MIN_ELONGATION)


def rad(x: float) -> float:
    return math.radians(x)


def jd(when: datetime) -> float:
    return (when - J2000).total_seconds() / 86400 + 2451545.0


def from_jd(value: float) -> datetime:
    return J2000 + timedelta(days=value - 2451545.0)


def _last_sunday(year: int, month: int) -> date:
    last = date(year, month + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def uk_offset(when: datetime) -> timedelta:
    """One hour during British Summer Time, otherwise none."""
    start = datetime.combine(_last_sunday(when.year, 3), datetime.min.time(), UTC) + timedelta(hours=1)
    end = datetime.combine(_last_sunday(when.year, 10), datetime.min.time(), UTC) + timedelta(hours=1)
    return timedelta(hours=1) if start <= when < end else timedelta(0)


def to_local(when: datetime) -> datetime:
    return (when + uk_offset(when)).replace(tzinfo=None)


def local_time(d: date, hour: float = 0) -> datetime:
    """UTC time of the given UK clock hour (0 = midnight starting local day d)."""
    noon = datetime(d.year, d.month, d.day, 12, tzinfo=UTC)
    return datetime(d.year, d.month, d.day, tzinfo=UTC) - uk_offset(noon) + timedelta(hours=hour)


def compass(azimuth: float) -> str:
    return COMPASS[int((azimuth % 360) / 45 + 0.5) % 8]


# ---- positions ----------------------------------------------------------------------------------

def ecliptic_to_equatorial(lon: float, lat: float, when_jd: float) -> tuple[float, float]:
    """Right ascension and declination in degrees from ecliptic longitude and latitude in degrees."""
    eps = rad(23.439 - 0.0000004 * (when_jd - 2451545.0))
    lam, beta = rad(lon), rad(lat)
    ra = math.atan2(math.sin(lam) * math.cos(eps) - math.tan(beta) * math.sin(eps), math.cos(lam))
    dec = math.asin(math.sin(beta) * math.cos(eps) + math.cos(beta) * math.sin(eps) * math.sin(lam))
    return math.degrees(ra) % 360, math.degrees(dec)


def alt_az(ra: float, dec: float, when_jd: float, lat: float, lon: float) -> tuple[float, float]:
    """Altitude above the horizon and compass bearing (north 0, east 90), all in degrees."""
    lst = rad(280.46061837 + 360.98564736629 * (when_jd - 2451545.0) + lon)
    h = lst - rad(ra)
    la, de = rad(lat), rad(dec)
    alt = math.asin(math.sin(de) * math.sin(la) + math.cos(de) * math.cos(la) * math.cos(h))
    az = math.atan2(math.sin(h), math.cos(h) * math.sin(la) - math.tan(de) * math.cos(la)) + math.pi
    return math.degrees(alt), math.degrees(az) % 360


def sun_longitude(when_jd: float) -> float:
    n = when_jd - 2451545.0
    g = rad(357.528 + 0.9856003 * n)
    return (280.460 + 0.9856474 * n + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360


def sun_alt_az(when: datetime, lat: float, lon: float) -> tuple[float, float]:
    j = jd(when)
    ra, dec = ecliptic_to_equatorial(sun_longitude(j), 0, j)
    return alt_az(ra, dec, j, lat, lon)


def moon_position(when_jd: float) -> tuple[float, float]:
    """Ecliptic longitude and latitude of the moon in degrees."""
    t = (when_jd - 2451545.0) / 36525
    lm = 218.3164477 + 481267.88123421 * t
    d = rad(297.8501921 + 445267.1114034 * t)
    m = rad(357.5291092 + 35999.0502909 * t)
    mp = rad(134.9633964 + 477198.8675055 * t)
    f = rad(93.2720950 + 483202.0175233 * t)
    lon = (lm + 6.288774 * math.sin(mp) + 1.274027 * math.sin(2 * d - mp) + 0.658314 * math.sin(2 * d)
           + 0.213618 * math.sin(2 * mp) - 0.185116 * math.sin(m) - 0.114332 * math.sin(2 * f)
           + 0.058793 * math.sin(2 * d - 2 * mp) + 0.057066 * math.sin(2 * d - m - mp)
           + 0.053322 * math.sin(2 * d + mp) + 0.045758 * math.sin(2 * d - m) - 0.040923 * math.sin(m - mp)
           - 0.034720 * math.sin(d) - 0.030383 * math.sin(m + mp))
    lat = (5.128122 * math.sin(f) + 0.280602 * math.sin(mp + f) + 0.277693 * math.sin(mp - f)
           + 0.173237 * math.sin(2 * d - f))
    return lon % 360, lat


def moon_alt_az(when: datetime, lat: float, lon: float) -> tuple[float, float]:
    j = jd(when)
    return alt_az(*ecliptic_to_equatorial(*moon_position(j), j), j, lat, lon)


def moon_phase(when: datetime) -> dict:
    """Illumination (0 to 1), waxing or not, age in days and the phase name."""
    j = jd(when)
    e = (moon_position(j)[0] - sun_longitude(j)) % 360
    names = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous",
             "Full moon", "Waning gibbous", "Last quarter", "Waning crescent"]
    return {"illum": (1 - math.cos(rad(e))) / 2, "waxing": e < 180, "age": e / 360 * SYNODIC,
            "name": names[int(e / 45 + 0.5) % 8]}


# ---- new moon, full moon and the quarters (Meeus, Astronomical Algorithms chapter 49) -------------

# (coefficient, needs E, multiple of M, of M', of F) for new moon and full moon
_NEW = [(-0.40720, 0, 0, 1, 0), (0.17241, 1, 1, 0, 0), (0.01608, 0, 0, 2, 0), (0.01039, 0, 0, 0, 2),
        (0.00739, 1, 1, -1, 0), (-0.00514, 1, 1, 1, 0), (0.00208, 2, 2, 0, 0), (-0.00111, 0, 0, -1, 2),
        (-0.00057, 0, 0, 1, 2), (0.00056, 1, 1, 2, 0), (-0.00042, 0, 0, 3, 0), (0.00042, 1, 1, 0, 2),
        (0.00038, 1, 1, 0, -2), (-0.00024, 1, -1, -2, 0)]
_FULL = [(-0.40614, *_NEW[0][1:]), (0.17302, *_NEW[1][1:]), (0.01614, *_NEW[2][1:]), (0.01043, *_NEW[3][1:]),
         (0.00734, *_NEW[4][1:]), (-0.00515, *_NEW[5][1:]), (0.00209, *_NEW[6][1:])] + _NEW[7:]


def phase_time(k: float) -> datetime:
    """UTC time of lunation k: whole numbers are new moons and .5 full moons (quarters use the mean time)."""
    t = k / 1236.85
    j = 2451550.09766 + SYNODIC * k + 0.00015437 * t * t
    if k % 0.5:
        return from_jd(j)
    e = 1 - 0.002516 * t
    m = rad(2.5534 + 29.10535670 * k)
    mp = rad(201.5643 + 385.81693528 * k)
    f = rad(160.7108 + 390.67050284 * k)
    total = sum(c * e ** power * math.sin(mm * m + pp * mp + ff * f)
                for c, power, mm, pp, ff in (_FULL if k % 1 else _NEW))
    return from_jd(j + total)


def phases_after(start: datetime, count: int) -> list[tuple[datetime, str]]:
    """The next count new, first quarter, full and last quarter moons after start."""
    k = math.floor((jd(start) - 2451550.09766) / SYNODIC) - 1
    names = ["New moon", "First quarter", "Full moon", "Last quarter"]
    out, q = [], 0
    while len(out) < count:
        when = phase_time(k + q / 4)
        if when > start:
            out.append((when, names[q % 4]))
        q += 1
    return out


def next_phase(start: datetime, name: str) -> datetime:
    return next(w for w, n in phases_after(start, 8) if n == name)


# ---- rising and setting ----------------------------------------------------------------------

def crossings(altitude, start: datetime, hours: float, threshold: float, step_min: int = 6) -> list[tuple[datetime, str]]:
    """When altitude(utc time) crosses threshold degrees in the window: [(utc time, 'rise' or 'set'), ...]."""
    out, prev_when, prev = [], start, altitude(start) - threshold
    for i in range(1, int(hours * 60 / step_min) + 1):
        when = start + timedelta(minutes=i * step_min)
        cur = altitude(when) - threshold
        if (prev < 0) != (cur < 0):
            out.append((prev_when + (when - prev_when) * (prev / (prev - cur)), "rise" if cur >= 0 else "set"))
        prev_when, prev = when, cur
    return out


def sun_events(d: date, lat: float, lon: float, threshold: float) -> dict:
    """For local day d: when the sun first rises above and first sets below threshold degrees (or None)."""
    found = crossings(lambda w: sun_alt_az(w, lat, lon)[0], local_time(d), 24, threshold)
    return {kind: next((w for w, k in found if k == kind), None) for kind in ("rise", "set")}


def moon_events(d: date, lat: float, lon: float) -> dict:
    found = crossings(lambda w: moon_alt_az(w, lat, lon)[0], local_time(d), 24, MOON_RISE, 10)
    return {kind: next((w for w, k in found if k == kind), None) for kind in ("rise", "set")}


def daylight_hours(d: date, lat: float, lon: float) -> float:
    """Hours of daylight from the sun's declination at noon: a smooth curve for the year chart."""
    j = jd(local_time(d, 12))
    dec = rad(ecliptic_to_equatorial(sun_longitude(j), 0, j)[1])
    cos_h = (math.sin(rad(SUN_RISE)) - math.sin(rad(lat)) * math.sin(dec)) / (math.cos(rad(lat)) * math.cos(dec))
    return 0.0 if cos_h >= 1 else 24.0 if cos_h <= -1 else 2 * math.degrees(math.acos(cos_h)) / 15


def season_starts(year: int) -> list[tuple[str, datetime]]:
    """Equinoxes and solstices: the moments the sun's longitude reaches 0, 90, 180 and 270 degrees."""
    out = []
    for name, target, month in (("March equinox", 0, 3), ("June solstice", 90, 6),
                                ("September equinox", 180, 9), ("December solstice", 270, 12)):
        lo, hi = datetime(year, month, 10, tzinfo=UTC), datetime(year, month, 30, tzinfo=UTC)
        for _ in range(40):
            mid = lo + (hi - lo) / 2
            if (sun_longitude(jd(mid)) - target + 180) % 360 - 180 < 0:
                lo = mid
            else:
                hi = mid
        out.append((name, lo))
    return out


# ---- planets ---------------------------------------------------------------------------------

def planet_alt_az(name: str, when: datetime, lat: float, lon: float) -> tuple[float, float]:
    """Rough position: the planet's orbit is treated as lying in the plane of Earth's, so a few degrees out."""
    t = (when - J2000).total_seconds() / 86400 / 36525
    ex, ey = _heliocentric("Earth", t)
    px, py = _heliocentric(name, t)
    ecliptic_lon = math.degrees(math.atan2(py - ey, px - ex)) % 360
    j = jd(when)
    return alt_az(*ecliptic_to_equatorial(ecliptic_lon, 0, j), j, lat, lon)
