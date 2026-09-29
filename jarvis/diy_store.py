"""Shared bits for the DIY abilities: numbers in metres, the saved rooms (diy-rooms.json) and table cards."""

import math

import homestore as hs
import screen
from config import Settings

ROOMS = "diy-rooms.json"
UNITS = {"m": 1.0, "cm": 0.01, "mm": 0.001, "ft": 0.3048, "in": 0.0254}
WALLS = ("north", "east", "south", "west")
MAX_ROOMS, MAX_ITEMS = 40, 60


def metres(value, what: str, unit="m", low: float = 0.01, high: float = 200) -> float:
    """A length converted to metres from m, cm, mm, ft or in."""
    factor = UNITS.get(hs.clean(unit).lower() or "m")
    if factor is None:
        raise ValueError("Use metres, cm, mm, ft or in for the units.")
    return round(hs.number(value, what, low / factor, high / factor) * factor, 4)


def count(value, what: str, high: int = 100_000) -> int:
    return int(hs.number(value if value is not None else 0, what, 0, high))


def up(n: float) -> int:
    """Round up, ignoring floating point dust like 4.000000001."""
    return math.ceil(round(n, 6))


def with_extra(n: float, pct) -> float:
    return n * (1 + hs.number(pct, "wastage", 0, 100) / 100)


def rooms(settings: Settings) -> dict:
    return {k: v for k, v in hs.load(settings, ROOMS, {}).items() if isinstance(v, dict)}


def save_rooms(settings: Settings, found: dict) -> None:
    hs.save(settings, ROOMS, found)


def room_key(found: dict, name) -> str:
    k = hs.find(found, hs.need(name, "room"))
    if k is None:
        raise ValueError(f"I haven't got a room called {hs.clean(name)} in the measurements book.")
    return k


def wall_area(room: dict) -> float:
    """Walls less doors (about 1.6 square metres each) and windows (about 1.2)."""
    walls = 2 * (room["length"] + room["width"]) * room["height"]
    return max(0.0, walls - 1.6 * len(room.get("doors", [])) - 1.2 * len(room.get("windows", [])))


def table(title: str, columns: list[str], rows: list[list], card_id: str, buttons=None) -> dict:
    return screen.card("table", title, card_id, columns=columns, rows=rows, buttons=buttons)


def sq(n: float) -> str:
    return f"{n:.1f} m²"
