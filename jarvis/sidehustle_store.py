"""Shared bits for the side-hustle abilities: sidehustle-*.json files in the memory folder, money, dates, logs.

Files: sidehustle-profile.json (skills, hours, budget, shortlist, monthly goal), sidehustle-hustles.json (your hustles
with their 30-day plans), sidehustle-log.json (hours, income and costs), sidehustle-orders.json, sidehustle-customers.json
(notes) and sidehustle-reviews.json. Everything stays on this PC; nothing is sent, posted or paid anywhere.
"""

from datetime import date, timedelta

import screen
from config import Settings
from creatorbiz_store import clean, find, gbp, load, need, parse_date, save, short, today, until  # noqa: F401 (re-exported)

PROFILE = "sidehustle-profile.json"
HUSTLES = "sidehustle-hustles.json"
LOG = "sidehustle-log.json"
ORDERS = "sidehustle-orders.json"
CUSTOMERS = "sidehustle-customers.json"
REVIEWS = "sidehustle-reviews.json"
MAX_ROWS = 2000
WAGE = 12.71  # UK National Living Wage from April 2026, a yardstick only; check GOV.UK for the current rate
HONEST = "This is general information and a planning estimate, not a promise of income."
TAX_NOTE = "Tax and rules differ for everyone, so check GOV.UK for the current rules."

CALC = "sidehustle-calc"
IDEAS = "sidehustle-ideas"
COMPARE = "sidehustle-compare"
PLAN = "sidehustle-plan"
GOAL = "sidehustle-goal"
HOURS = "sidehustle-hours"
REVIEW = "sidehustle-review"
FLAGS = "sidehustle-redflags"
screen.EXTRA_KINDS.update({CALC, IDEAS, COMPARE, PLAN, GOAL, HOURS, REVIEW, FLAGS})


def number(value, what: str, allow_zero: bool = False, top: float = 1_000_000) -> float:
    try:
        n = float(str(value if value is not None else "").replace("£", "").replace(",", "").strip())
    except ValueError:
        raise ValueError(f"Give the {what} as a number.") from None
    if n < 0 or (n == 0 and not allow_zero) or n > top:
        raise ValueError(f"That {what} doesn't look right.")
    return round(n, 2)


def pct(value, what: str = "percentage") -> float:
    return number(value, what, allow_zero=True, top=99)


def num(n: float) -> str:
    return f"{n:g}" if abs(n * 10 - round(n * 10)) < 1e-9 else f"{n:.2f}"


def calc(text: str, title: str, headline: str, sub: str = "", rows=None, notes=None, buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card(CALC, title, "", buttons=buttons, data={
        "headline": headline, "sub": sub, "rows": [[str(a), str(b)] for a, b in (rows or [])],
        "notes": list(notes or [])}))


def profile(settings: Settings) -> dict:
    return load(settings, PROFILE, {})


def hustles(settings: Settings) -> list[dict]:
    return [h for h in load(settings, HUSTLES, []) if isinstance(h, dict)]


def pick_hustle(settings: Settings, name=None, need_one: bool = True) -> dict | None:
    rows = hustles(settings)
    if clean(name):
        key = find([h["name"] for h in rows], name)
        hit = next((h for h in rows if h["name"] == key), None)
        if hit is None and need_one:
            raise ValueError(f"I don't have a side hustle called {clean(name)}.")
        return hit
    live = [h for h in rows if h.get("status") == "active"] or rows
    if len(live) == 1:
        return live[0]
    if need_one:
        raise ValueError("Which side hustle?" if live else "You haven't started a side hustle yet.")
    return None


def update_hustle(settings: Settings, hustle: dict) -> None:
    save(settings, HUSTLES, [hustle if h["name"] == hustle["name"] else h for h in hustles(settings)])


def hustle_name(settings: Settings, name) -> str:
    """The saved hustle's name if it matches, else the typed name, else the only hustle."""
    hit = pick_hustle(settings, name, need_one=False)
    if hit:
        return hit["name"]
    if clean(name):
        return clean(name, 60)
    return pick_hustle(settings)["name"]


def log(settings: Settings) -> list[dict]:
    return [e for e in load(settings, LOG, []) if isinstance(e, dict)]


def add_entry(settings: Settings, kind: str, hustle: str, amount: float, note: str = "", day: date | None = None,
              customer: str = "") -> dict:
    rows = log(settings)
    if len(rows) >= MAX_ROWS:
        raise ValueError("The log is full; tidy it before adding more.")
    entry = {"date": (day or today()).isoformat(), "hustle": hustle, "kind": kind, "amount": amount, "note": note,
             "customer": customer}
    rows.append(entry)
    save(settings, LOG, rows)
    return entry


def totals(rows: list[dict], hustle: str | None = None, start: date | None = None, end: date | None = None) -> dict:
    out = {"income": 0.0, "costs": 0.0, "hours": 0.0}
    for e in rows:
        if hustle and e["hustle"].lower() != hustle.lower():
            continue
        day = date.fromisoformat(e["date"])
        if (start and day < start) or (end and day > end):
            continue
        key = {"income": "income", "expense": "costs", "hours": "hours"}[e["kind"]]
        out[key] += float(e["amount"])
    out["profit"] = round(out["income"] - out["costs"], 2)
    out["rate"] = round(out["profit"] / out["hours"], 2) if out["hours"] else None
    return out


def month_bounds(text=None) -> tuple[date, date]:
    t = clean(text)
    try:
        first = date.fromisoformat(t + "-01") if t else today().replace(day=1)
    except ValueError:
        raise ValueError("Give the month as YYYY-MM.") from None
    nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first, nxt - timedelta(days=1)


def rate_text(rate) -> str:
    return "not enough hours logged" if rate is None else f"{gbp(rate)} an hour"
