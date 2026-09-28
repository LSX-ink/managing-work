"""Shared bits for the money-plus abilities: their JSON files, month maths and the "finance" pop-up board.

A finance board is a pop-up of stacked sections, drawn by frontend/popup-money-plus.js:
  meters {rows: [{label, value, max, note?, over?, say?}]}   progress bars (spent vs budget, saved vs target)
  stats  {items: [{label, value}]}                           big numbers in a grid
  chart  {chart: {type, labels, values, unit}}              the usual bar or line chart
  table  {columns, rows}
  list   {items: [{label, say?}]}                           clicking an item with say sends it to Alfred
Every section can have a title.
"""

import re
from collections import defaultdict
from datetime import date

import homestore as hs
import money
import screen
from config import Settings

screen.EXTRA_KINDS.add("finance")

BUDGETS, POTS, ENVELOPES, NETWORTH = "finance-budgets.json", "finance-pots.json", "finance-envelopes.json", "finance-networth.json"
RECEIPTS, DEBTS, PAYDAY, TRIPS, IOUS = "finance-receipts.json", "finance-debts.json", "finance-payday.json", "finance-trips.json", "finance-ious.json"
MAX_ROWS = 100
MAX_LOG = 2000


def rows(settings: Settings, name: str) -> dict:
    return {k: v for k, v in hs.load(settings, name, {}).items() if isinstance(v, dict)}


def put(settings: Settings, name: str, found: dict, key: str, value) -> None:
    if key not in found and len(found) >= MAX_ROWS:
        raise ValueError("That list is full; remove something first.")
    found[key] = value
    hs.save(settings, name, found)


def key_of(found: dict, name, what: str) -> str:
    key = hs.find(found, hs.need(name, what))
    if key is None:
        raise ValueError(f"I haven't got a {what} called {hs.clean(name)}.")
    return key


def amount(value, what: str = "amount", low: float = 0) -> float:
    return round(hs.number(value, what, low, 10_000_000), 2)


def cash(n: float, settings_or_currency) -> str:
    cur = settings_or_currency if isinstance(settings_or_currency, str) else settings_or_currency.currency
    return hs.money(n, cur)


def month_of(value, today: date) -> str:
    text = hs.clean(value)
    if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", text):
        return text[:7]
    if text and text.lower() not in ("this month", "now"):
        raise ValueError("Give the month as YYYY-MM, e.g. 2026-08.")
    return today.strftime("%Y-%m")


def month_back(month: str, n: int) -> str:
    y, m = int(month[:4]), int(month[5:7]) - n
    while m < 1:
        y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"


def month_name(month: str) -> str:
    return date(int(month[:4]), int(month[5:7]), 1).strftime("%B %Y")


def spending(settings: Settings) -> list[dict]:
    return [s for s in money.load(settings)["spending"]
            if isinstance(s, dict) and isinstance(s.get("amount"), (int, float)) and s.get("date")]


def spent_by_category(settings: Settings, month: str) -> dict[str, float]:
    by = defaultdict(float)
    for s in spending(settings):
        if s["date"].startswith(month):
            by[(s.get("category") or "other").lower()] += s["amount"]
    return dict(by)


def budgets(settings: Settings) -> dict[str, float]:
    return {k: float(v) for k, v in hs.load(settings, BUDGETS, {}).items() if isinstance(v, (int, float))}


def budget_left(settings: Settings, month: str) -> float:
    spent = spent_by_category(settings, month)
    return round(sum(max(0.0, b - spent.get(c, 0.0)) for c, b in budgets(settings).items()), 2)


# ---- the pop-up board ---------------------------------------------------------------------------

def meter(label, value, top, settings, say: str = "", note: str = "") -> dict:
    value, top = round(float(value), 2), round(float(top), 2)
    row = {"label": hs.clean(label, 60), "value": value, "max": top,
           "note": note or f"{cash(value, settings)} of {cash(top, settings)}", "over": value > top}
    if say:
        row["say"] = hs.clean(say, 200)
    return row


def section(kind: str, title: str = "", **fields) -> dict:
    return {"type": kind, "title": hs.clean(title, 60), **fields}


def chart(labels, values, kind: str = "bar", unit: str = "", title: str = "") -> dict:
    labels, values = list(labels)[-60:], [round(float(v), 2) for v in list(values)[-60:]]
    return section("chart", title, chart={"type": kind, "labels": [hs.clean(x, 30) for x in labels],
                                          "values": values, "unit": unit[:12]})


def stats(pairs, title: str = "") -> dict:
    return section("stats", title, items=[{"label": hs.clean(k, 40), "value": hs.clean(v, 60)} for k, v in pairs])


def table(columns, body, title: str = "") -> dict:
    return section("table", title, columns=[hs.clean(c, 40) for c in columns],
                   rows=[[hs.clean(c, 120) for c in r] for r in list(body)[:200]])


def board(text: str, title: str, card_id: str, sections: list[dict], buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card("finance", title, card_id, buttons=buttons, data={"sections": sections}))
