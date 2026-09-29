"""Shared bits for the photography abilities: reading numbers like 1/125 or f/2.8, sensor sizes and card helpers."""

import math

import homestore as hs
import screen
from screen import Shown

SHUTTERS = [1 / 8000, 1 / 6400, 1 / 5000, 1 / 4000, 1 / 3200, 1 / 2500, 1 / 2000, 1 / 1600, 1 / 1250, 1 / 1000,
            1 / 800, 1 / 640, 1 / 500, 1 / 400, 1 / 320, 1 / 250, 1 / 200, 1 / 160, 1 / 125, 1 / 100, 1 / 80,
            1 / 60, 1 / 50, 1 / 40, 1 / 30, 1 / 25, 1 / 20, 1 / 15, 1 / 13, 1 / 10, 1 / 8, 1 / 6, 1 / 5, 1 / 4,
            0.3, 0.4, 0.5, 0.6, 0.8, 1, 1.3, 1.6, 2, 2.5, 3.2, 4, 5, 6, 8, 10, 13, 15, 20, 25, 30]
APERTURES = [1.0, 1.2, 1.4, 1.6, 1.8, 2, 2.2, 2.5, 2.8, 3.2, 3.5, 4, 4.5, 5, 5.6, 6.3, 7.1, 8, 9, 10, 11, 13, 14, 16,
             18, 20, 22, 25, 29, 32, 45, 64]
ISOS = [50, 64, 80, 100, 125, 160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000,
        5000, 6400, 8000, 10000, 12800, 25600, 51200, 102400]
# Sensor width x height in mm.
SENSORS = {"full frame": (36, 24), "aps-c": (23.6, 15.6), "aps-c canon": (22.3, 14.9),
           "micro four thirds": (17.3, 13), "1 inch": (13.2, 8.8), "medium format": (43.8, 32.9),
           "phone": (7.0, 5.3)}
SENSOR_ALIASES = {"ff": "full frame", "full": "full frame", "fullframe": "full frame", "35mm": "full frame",
                  "apsc": "aps-c", "aps c": "aps-c", "crop": "aps-c", "nikon": "aps-c", "sony": "aps-c",
                  "fuji": "aps-c", "canon aps-c": "aps-c canon", "canon": "aps-c canon",
                  "mft": "micro four thirds", "m43": "micro four thirds", "four thirds": "micro four thirds",
                  "1\"": "1 inch", "1-inch": "1 inch", "one inch": "1 inch", "gfx": "medium format",
                  "iphone": "phone", "smartphone": "phone", "mobile": "phone"}
SENSOR_NAMES = ", ".join(SENSORS)
FULL_DIAGONAL = math.hypot(36, 24)


def num(value, what: str, low: float, high: float) -> float:
    return hs.number(value, what, low, high)


def shutter(value, what: str = "shutter speed") -> float:
    """Seconds from 1/125, 0.5, '2s' or '1/125 s'."""
    text = str(value if value is not None else "").strip().lower().replace('"', "").replace("sec", "")
    text = text.rstrip("s").strip()
    try:
        if "/" in text:
            top, bottom = text.split("/", 1)
            seconds = float(top) / float(bottom)
        else:
            seconds = float(text)
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"The {what} must be like 1/125 or 2 (seconds).") from None
    if not 1 / 100_000 <= seconds <= 86_400:
        raise ValueError(f"That {what} doesn't look right.")
    return seconds


def aperture(value, what: str = "aperture") -> float:
    text = str(value if value is not None else "").lower().replace("f/", "").replace("f", "").strip()
    return num(text, what, 0.7, 128)


def nearest(value: float, ladder: list) -> float:
    """The closest standard third-stop value on a ladder, judged in stops."""
    return min(ladder, key=lambda x: abs(math.log2(x / value)))


def fmt_shutter(seconds: float) -> str:
    if seconds >= 60:
        whole = round(seconds)
        hours, rest = divmod(whole, 3600)
        minutes, secs = divmod(rest, 60)
        return " ".join(p for p in (f"{hours} h" if hours else "", f"{minutes} min" if minutes else "",
                                    f"{secs} s" if secs else "") if p)
    if seconds >= 0.3:
        return f"{seconds:.1f}".rstrip("0").rstrip(".") + " s"
    return f"1/{round(1 / seconds)} s"


def fmt_ap(n: float) -> str:
    return f"f/{n:.1f}".replace(".0", "") if n < 10 else f"f/{n:.0f}"


def stops(ratio: float) -> str:
    return f"{math.log2(ratio):+.1f} stops".replace(".0 ", " ")


def sensor(a) -> tuple[str, float, float, float]:
    """(name, width mm, height mm, crop factor) from a sensor name or a crop factor. Default full frame."""
    crop = a("crop_factor")
    if crop is not None:
        c = num(crop, "crop factor", 0.5, 10)
        width = 36 / c
        return f"crop {c:g}", width, width * 2 / 3, c
    name = hs.clean(a("sensor")).lower() or "full frame"
    name = SENSOR_ALIASES.get(name, name)
    if name not in SENSORS:
        raise ValueError(f"I know these sensor sizes: {SENSOR_NAMES}. Or give a crop_factor.")
    w, h = SENSORS[name]
    return name, w, h, round(FULL_DIAGONAL / math.hypot(w, h), 2)


def metres(a, key: str = "distance_m", what: str = "distance", low: float = 0.05, high: float = 100_000) -> float:
    """A distance in metres from key, or from distance_ft when the user gave feet."""
    if a("distance_ft") is not None and a(key) is None:
        return num(a("distance_ft"), what, low, high) * 0.3048
    return num(a(key), what, low, high)


def fmt_m(m: float) -> str:
    if math.isinf(m):
        return "infinity"
    return f"{m:.2f} m" if m < 10 else f"{m:.1f} m" if m < 1000 else f"{m / 1000:.2f} km"


def table(title: str, columns: list[str], rows: list[list], card_id: str, buttons=None) -> dict:
    return screen.card("table", title, card_id, columns=columns, rows=rows, buttons=buttons)


def facts(title: str, rows: list[list], card_id: str, spoken: str) -> Shown:
    """A table of thing, value and an optional note, with a short spoken line."""
    wide = any(len(r) > 2 for r in rows)
    cols = ["", "Value", "Notes"] if wide else ["", "Value"]
    rows = [list(r) + [""] * (len(cols) - len(r)) for r in rows]
    return Shown(spoken, table(title, cols, rows, card_id))
