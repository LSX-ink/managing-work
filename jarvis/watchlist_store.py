"""Shared bits for the watchlist abilities: films, TV and books in one watchlist.json, and the "watchlist" pop-up.

watchlist.json (in the memory folder) holds items (films and shows), books, reading_log (pages per day), goal (books
per year), lends, club (the book club) and nights (film nights). It is separate from the older, simpler reading
and watch lists; nothing there is changed.

A watchlist board is a pop-up of stacked sections, drawn by frontend/popup-watchlist.js:
  gallery {tiles: [{title, subtitle?, badge?, stars?, image?, say?}]}   poster-style tiles
  meters  {rows: [{label, value, max, note?, say?}]}                    progress bars
  ring    {value, max, label, note?}                                    a goal ring
  stats   {items: [{label, value}]}   chart {chart}   table {columns, rows}   text {text}
  list    {items: [{label, say?}]}                                      clicking an item with say sends it to Alfred
Every section can have a title.
"""

import re
import zlib

import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.add("watchlist")

FILE = "watchlist.json"
MAX_ITEMS = 1500
KEYS = {"items": list, "books": list, "lends": list, "nights": list, "reading_log": dict, "goal": dict, "club": dict}


def load(settings: Settings) -> dict:
    data = hs.load(settings, FILE, {})
    for key, kind in KEYS.items():
        if not isinstance(data.get(key), kind):
            data[key] = kind()
    return data


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def add_capped(rows: list, row: dict, what: str) -> None:
    if len(rows) >= MAX_ITEMS:
        raise ValueError(f"Your {what} list is full; remove something first.")
    rows.append(row)


def named(rows: list, title, what: str, field: str = "title", **must) -> dict:
    """The row whose field matches title (exact, else the only partial match); friendly error if none."""
    pool = [r for r in rows if isinstance(r, dict) and all(r.get(k) == v for k, v in must.items())]
    key = hs.find([str(r.get(field, "")) for r in pool], hs.need(title, what, 120))
    found = next((r for r in pool if str(r.get(field, "")) == key), None) if key is not None else None
    if found is None:
        raise ValueError(f"I can't find a {what} called {hs.clean(title)}. Check the name.")
    return found


def stars_of(rating) -> str:
    n = rating if isinstance(rating, int) and 1 <= rating <= 5 else 0
    return "★" * n + "☆" * (5 - n) if n else ""


def rating_of(value, required: bool = False) -> int | None:
    if value is None or value == "":
        if required:
            raise ValueError("Give a rating from 1 to 5 stars.")
        return None
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        raise ValueError("Rate it from 1 to 5 stars.") from None
    if not 1 <= n <= 5:
        raise ValueError("Rate it from 1 to 5 stars.")
    return n


def minutes_of(value) -> int:
    return int(hs.number(value, "length in minutes", 0, 2000)) if value not in (None, "") else 0


def words(value, limit: int = 8) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[,;]| and ", value)
    return [hs.clean(v, 40) for v in (value or []) if hs.clean(v, 40)][:limit]


def https(url) -> str:
    url = str(url or "").strip()
    return url if url.startswith("https://") and len(url) < 2000 else ""


def average(ratings) -> float:
    ratings = [r for r in ratings if isinstance(r, int)]
    return round(sum(ratings) / len(ratings), 1) if ratings else 0.0


# ---- the pop-up board ---------------------------------------------------------------------------

def section(kind: str, title: str = "", **fields) -> dict:
    return {"type": kind, "title": hs.clean(title, 60), **fields}


def tile(title, subtitle="", badge="", stars="", image="", say="") -> dict:
    return {"title": hs.clean(title, 100), "subtitle": hs.clean(subtitle, 100), "badge": hs.clean(badge, 20),
            "stars": stars, "image": https(image), "say": hs.clean(say, 200), "tone": zlib.crc32(str(title).encode()) % 6}


def gallery(tiles, title: str = "") -> dict:
    return section("gallery", title, tiles=list(tiles)[:120])


def meter(label, value, top, note: str = "", say: str = "") -> dict:
    return {"label": hs.clean(label, 80), "value": round(float(value), 1), "max": round(float(top), 1),
            "note": hs.clean(note, 60), "say": hs.clean(say, 200)}


def stats(pairs, title: str = "") -> dict:
    return section("stats", title, items=[{"label": hs.clean(k, 40), "value": hs.clean(v, 60)} for k, v in pairs])


def chart(labels, values, kind: str = "bar", unit: str = "", title: str = "") -> dict:
    labels, values = list(labels)[-60:], [round(float(v), 2) for v in list(values)[-60:]]
    return section("chart", title, chart={"type": kind, "labels": [hs.clean(x, 30) for x in labels],
                                          "values": values, "unit": unit[:12]})


def table(columns, body, title: str = "") -> dict:
    return section("table", title, columns=[hs.clean(c, 40) for c in columns],
                   rows=[[hs.clean(c, 160) for c in r] for r in list(body)[:200]])


def lines(rows, title: str = "") -> dict:
    return section("list", title, items=[{"label": hs.clean(r[0] if isinstance(r, tuple) else r, 200),
                                          "say": hs.clean(r[1], 200) if isinstance(r, tuple) else ""} for r in list(rows)[:100]])


def board(text: str, title: str, card_id: str, sections: list[dict], buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card("watchlist", title, card_id, buttons=buttons, data={"sections": sections}))
