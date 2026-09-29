"""Shared bits for the creator-business abilities: creatorbiz-*.json files in the memory folder, money, dates, matching.

Files: creatorbiz-deals.json (brand deals with deliverables and contract ticks), creatorbiz-invoices.json,
creatorbiz-ledger.json (income and expenses), creatorbiz-gifts.json (gifted products and affiliate links) and
creatorbiz-profile.json (media kit facts and rate card numbers). Kit and drafts are saved as files in the
"Creator business" folder. Everything stays on this PC; nothing is ever sent or posted.
"""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import memory
from config import Settings

DEALS = "creatorbiz-deals.json"
INVOICES = "creatorbiz-invoices.json"
LEDGER = "creatorbiz-ledger.json"
GIFTS = "creatorbiz-gifts.json"
PROFILE = "creatorbiz-profile.json"
FOLDER = "Creator business"
MAX_ROWS = 400
HONEST = "This is a planning estimate, not a promise of income."


def today() -> date:
    return datetime.now().date()


def load(settings: Settings, name: str, default):
    try:
        found = json.loads((memory.root(settings) / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return found if isinstance(found, type(default)) else default


def save(settings: Settings, name: str, data) -> None:
    path = memory.root(settings) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_file(settings: Settings, name: str, text: str) -> Path:
    """Save a text file in the Creator business folder without overwriting an older one."""
    folder = memory.root(settings) / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = memory.unique_path(folder / memory.safe_name(name, "file name"))
    path.write_text(text, encoding="utf-8")
    return path


def clean(value, limit: int = 80) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def need(value, what: str, limit: int = 80) -> str:
    text = clean(value, limit)
    if not text:
        raise ValueError(f"Which {what}?")
    return text


def find(keys, name: str) -> str | None:
    """The key matching name exactly (ignoring case), else the only one containing it."""
    name = clean(name).lower()
    keys = list(keys)
    exact = next((k for k in keys if k.lower() == name), None)
    if exact is not None or not name:
        return exact
    part = [k for k in keys if name in k.lower()]
    return part[0] if len(part) == 1 else None


def money(value, what: str = "amount", allow_zero: bool = False) -> float:
    text = str(value if value is not None else "").replace("£", "").replace(",", "").strip()
    try:
        number = round(float(text), 2)
    except ValueError:
        raise ValueError(f"Give the {what} as a number of pounds.") from None
    if number < 0 or (number == 0 and not allow_zero) or number > 10_000_000:
        raise ValueError(f"That {what} doesn't look right.")
    return number


def gbp(value: float) -> str:
    return f"£{value:,.0f}" if float(value).is_integer() else f"£{value:,.2f}"


def parse_date(value, what: str = "date") -> date | None:
    text = clean(value).lower()
    if not text:
        return None
    offsets = {"today": 0, "tomorrow": 1, "yesterday": -1, "next week": 7}
    if text in offsets:
        return today() + timedelta(days=offsets[text])
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"Give the {what} as YYYY-MM-DD.") from None


def until(day: date, ref: date | None = None) -> str:
    n = (day - (ref or today())).days
    if n == 0:
        return "today"
    if n == 1:
        return "tomorrow"
    if n == -1:
        return "1 day overdue"
    return f"in {n} days" if n > 0 else f"{-n} days overdue"


def short(day: date) -> str:
    return f"{day.day} {day.strftime('%b')}"


def long_date(day: date) -> str:
    return f"{day.day} {day.strftime('%B %Y')}"


def deals(settings: Settings) -> list[dict]:
    return [d for d in load(settings, DEALS, []) if isinstance(d, dict)]


def pick_deal(rows: list[dict], brand, campaign=None) -> dict:
    name = need(brand, "brand")
    hits = [d for d in rows if d["brand"].lower() == name.lower()] or [d for d in rows if name.lower() in d["brand"].lower()]
    if campaign:
        hits = [d for d in hits if clean(campaign).lower() in d.get("campaign", "").lower()] or hits
    if not hits:
        raise ValueError(f"I don't have a deal with {name}.")
    if len(hits) > 1:
        raise ValueError(f"There are {len(hits)} deals with {name}; say which campaign.")
    return hits[0]


def deal_label(d: dict) -> str:
    return f"{d['brand']} - {d['campaign']}" if d.get("campaign") else d["brand"]


def ledger(settings: Settings) -> list[dict]:
    return [e for e in load(settings, LEDGER, []) if isinstance(e, dict)]


def add_ledger(settings: Settings, kind: str, amount: float, brand: str = "", note: str = "", category: str = "",
               day: date | None = None) -> dict:
    rows = ledger(settings)
    if len(rows) >= MAX_ROWS * 5:
        raise ValueError("The ledger is full; clear old entries first.")
    entry = {"date": (day or today()).isoformat(), "kind": kind, "amount": amount, "brand": brand,
             "note": note, "category": category}
    rows.append(entry)
    save(settings, LEDGER, rows)
    return entry
