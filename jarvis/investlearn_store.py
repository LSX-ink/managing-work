"""Shared bits for the investing-basics abilities: investlearn.json, the honesty line, growth maths and card builders.

EDUCATION AND CALCULATORS ONLY: no live prices, no network, never advice on what to buy. Every figure is an illustration
built from numbers the user picks; returns are not guaranteed and capital is at risk. UK rules are general information:
check GOV.UK for the current limits.
The file holds learning progress, risk questionnaire answers, the paper-only practice portfolio and planning goals.
"""

import homestore as hs
import screen
from config import Settings

FILE = "investlearn.json"
DISCLAIMER = "This is an illustration only: returns are not guaranteed, capital is at risk, and it is not financial advice."
PRACTICE = "Practice only: made-up holdings and prices you typed, not real money and not advice."
CHECK = "Rules and limits change: check GOV.UK for the current ones."
SECTIONS = {"lessons": {}, "quizzes": {}, "risk": {}, "holdings": [], "trades": [], "goals": [], "next_id": 1}
GROWTH, BARS, CARDS = "investlearn-growth", "investlearn-bars", "investlearn-cards"
screen.EXTRA_KINDS.update({GROWTH, BARS, CARDS})
MAX_ROWS = 500


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    return {k: found[k] if isinstance(found.get(k), type(v)) else type(v)() for k, v in SECTIONS.items()} | {
        "next_id": found.get("next_id") if isinstance(found.get("next_id"), int) else 1}


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def new_id(data: dict) -> int:
    n = data["next_id"]
    data["next_id"] += 1
    return n


def put(rows: list, item) -> None:
    if len(rows) >= MAX_ROWS:
        raise ValueError("That list is full; remove something first.")
    rows.append(item)


def confirm_needed(what: str) -> str:
    return f"Ask the user to confirm {what}. Only after a yes, call again with confirmed true."


def gbp(n: float) -> str:
    n = float(n)
    return f"£{n:,.0f}" if abs(n) >= 100 or n == int(n) else f"£{n:,.2f}"


def gbp2(n: float) -> str:
    return f"£{float(n):,.2f}"


def num(args: dict, key: str, what: str, default=None, low: float = 0, high: float = 1_000_000_000):
    value = args.get(key)
    if value is None or value == "":
        if default is None:
            raise ValueError(f"What is the {what}?")
        return default
    return hs.number(value, what, low, high)


def growth_card(title: str, card_id: str, labels: list, series: list[dict], lines: list[str], note: str = "",
                buttons=None, unit: str = "£") -> dict:
    """Multi-line chart: series are {name, values, style} where style is solid, dashed or dotted."""
    clean = [{"name": hs.clean(s["name"], 40), "style": s.get("style", "solid"),
              "values": [round(float(v), 2) for v in s["values"]]} for s in series[:6]]
    data = {"labels": [str(x) for x in labels[:80]], "series": clean, "lines": [hs.clean(x, 200) for x in lines[:12]],
            "note": hs.clean(note or DISCLAIMER, 300), "unit": unit}
    return screen.card(GROWTH, title, card_id, data=data, buttons=buttons)


def bars_card(title: str, card_id: str, rows: list[dict], note: str = "", buttons=None) -> dict:
    """Bars: rows of {label, value, max, text, say, warn}."""
    clean = [{"label": hs.clean(r["label"], 60), "value": round(float(r["value"]), 2), "max": round(float(r["max"]), 2),
              "text": hs.clean(r.get("text"), 80), "say": hs.clean(r.get("say"), 200), "warn": bool(r.get("warn"))}
             for r in rows[:20]]
    return screen.card(BARS, title, card_id, data={"rows": clean, "note": hs.clean(note or DISCLAIMER, 300)}, buttons=buttons)


def cards_card(title: str, card_id: str, cards: list[tuple], note: str = "", buttons=None) -> dict:
    """Tap-to-flip cards: (front, back) pairs, plus an optional say line as a third item."""
    rows = [{"front": hs.clean(c[0], 120), "back": hs.clean(c[1], 500), "say": hs.clean(c[2], 200) if len(c) > 2 else ""}
            for c in cards[:80]]
    return screen.card(CARDS, title, card_id, data={"cards": rows, "note": hs.clean(note, 300)}, buttons=buttons)


def table(title: str, card_id: str, columns: list, rows: list, buttons=None) -> dict:
    return screen.card("table", title, card_id, columns=columns, rows=rows, buttons=buttons)


# Growth maths -------------------------------------------------------------

MAX_YEARS = 80


def check_years(n: float) -> int:
    return int(hs.number(n, "number of years", 1, MAX_YEARS))


def check_rate(n: float, what: str = "rate") -> float:
    return hs.number(n, what, -50, 50)


def project(lump: float, monthly: float, years: int, rate: float, step: float = 0.0, fee: float = 0.0) -> dict:
    """Year-end balances (index 0..years) and money paid in. Monthly compounding of a yearly rate; step raises the monthly
    amount each year by that percent; fee is a yearly percent taken off the rate."""
    net = (rate - fee) / 100
    if net <= -1:
        raise ValueError("That rate doesn't look right.")
    grow = (1 + net) ** (1 / 12)
    bal, paid, put_in = lump, lump, monthly
    balances, contributions = [bal], [paid]
    for _year in range(years):
        for _m in range(12):
            bal = bal * grow + put_in
            paid += put_in
        put_in *= 1 + step / 100
        balances.append(bal)
        contributions.append(paid)
    return {"balances": balances, "paid": contributions}


def deflate(values: list, inflation: float) -> list:
    return [v / (1 + inflation / 100) ** i for i, v in enumerate(values)]


def spread_rates(rate: float, spread: float) -> tuple[float, float, float]:
    return rate - spread, rate, rate + spread


def year_labels(years: int) -> list:
    return [f"Yr {i}" for i in range(years + 1)]


def months_to(target: float, lump: float, monthly: float, rate: float, limit: int = 1200) -> int | None:
    """Whole months until the balance reaches target, or None when it takes more than limit months."""
    grow, balance = (1 + rate / 100) ** (1 / 12), lump
    for months in range(limit + 1):
        if balance >= target:
            return months
        balance = balance * grow + monthly
    return None


def add_months(day, months: int):
    total = day.month - 1 + months
    return day.replace(year=day.year + total // 12, month=total % 12 + 1, day=min(day.day, 28))
