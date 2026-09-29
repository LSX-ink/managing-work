"""Shared bits for the motoring abilities: everything lives in motoring.json in the memory folder (car profile,
due dates, service log, tyre notes, mileage and commute logs). The registration number is kept only in that file and
only drawn on the screen; it is never spoken back or sent anywhere."""

from datetime import date

import homestore as hs
from config import Settings

FILE = "motoring.json"
MAX_LOG = 2000
SECTIONS = {"profile": {}, "dates": {}, "service": [], "tyres": {}, "mileage": [], "commute": []}


def load(settings: Settings) -> dict:
    data = hs.load(settings, FILE, {})
    return {k: data[k] if isinstance(data.get(k), type(v)) else type(v)() for k, v in SECTIONS.items()}


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def add(settings: Settings, section: str, entry: dict) -> dict:
    data = load(settings)
    if len(data[section]) >= MAX_LOG:
        raise ValueError("That log is full; export it and clear some old entries first.")
    data[section].append(entry)
    save(settings, data)
    return data


def number(value, what: str, low: float = 0, high: float = 1_000_000) -> float:
    return hs.number(value, what, low, high)


def positive(value, what: str, high: float = 1_000_000) -> float:
    n = hs.number(value, what, 0, high)
    if n <= 0:
        raise ValueError(f"The {what} must be more than zero.")
    return n


def short(day: date) -> str:
    return f"{day.day} {day:%b %Y}"


def car_mpg(settings: Settings) -> float | None:
    mpg = load(settings)["profile"].get("mpg")
    return float(mpg) if mpg else None
