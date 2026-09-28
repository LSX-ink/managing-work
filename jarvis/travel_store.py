"""Shared bits for the travel abilities: trips in travel-trips.json, picking the trip meant, and country look-ups.

Built on homestore, so files live in the memory folder and dates follow the same rules (YYYY-MM-DD, 'today').
"""

from datetime import date

import homestore as hs
import travel_data
from config import Settings

TRIPS = "travel-trips.json"
MAX_TRIPS = 50
MAX_ITEMS = 200


def trips(settings: Settings) -> dict:
    return {k: v for k, v in hs.load(settings, TRIPS, {}).items() if isinstance(v, dict)}


def save(settings: Settings, found: dict) -> None:
    hs.save(settings, TRIPS, found)


def days(trip: dict) -> tuple[date, date]:
    return date.fromisoformat(trip["start"]), date.fromisoformat(trip["end"])


def pick(found: dict, name=None) -> str:
    """The trip meant: by name or destination, else the next one coming up (or on now), else the only one."""
    if not found:
        raise ValueError("You haven't got any trips yet. Tell me where and when first.")
    if hs.clean(name):
        k = hs.find(found, name)
        if k is None:
            places = {v.get("destination", ""): key for key, v in found.items()}
            dest = hs.find(places, name)
            k = places[dest] if dest is not None else None
        if k is None:
            raise ValueError(f"I haven't got a trip called {hs.clean(name)}. Trips: {', '.join(found)}.")
        return k
    today = hs.today()
    ahead = sorted((v["start"], k) for k, v in found.items() if days(v)[1] >= today)
    if ahead:
        return ahead[0][1]
    return max(found, key=lambda k: found[k]["start"])


def countdown(trip: dict) -> str:
    start, end = days(trip)
    today = hs.today()
    if today > end:
        return f"was {(today - end).days} days ago"
    if today >= start:
        return f"is on now (day {(today - start).days + 1} of {(end - start).days + 1})"
    n = (start - today).days
    return "starts tomorrow" if n == 1 else f"starts in {n} days"


def next_id(items: list) -> int:
    return max([i.get("id", 0) for i in items] + [0]) + 1


def by_id(items: list, number, what: str) -> dict:
    try:
        n = int(number)
    except (TypeError, ValueError):
        raise ValueError(f"Which {what}? Give its number from the list.") from None
    for item in items:
        if item.get("id") == n:
            return item
    raise ValueError(f"There's no {what} number {n}.")


def country(name) -> str:
    """The country table's name for a country (or a well-known place in one), or ValueError."""
    text = hs.clean(name).lower().strip(". ")
    if not text:
        raise ValueError("Which country?")
    if text in travel_data.ALIASES:
        return travel_data.ALIASES[text]
    for k in travel_data.COUNTRIES:
        if k.lower() == text or k.lower() == f"the {text}" or f"the {k.lower()}" == text:
            return k
    part = [k for k in travel_data.COUNTRIES if text in k.lower()]
    if len(part) == 1:
        return part[0]
    raise ValueError(f"I haven't got {hs.clean(name)} in my country table.")
