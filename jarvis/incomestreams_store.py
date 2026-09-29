"""Shared bits for the income streams abilities: incomestreams.json in the memory folder, months, tax years, sums.

The file holds streams (name, type active/passive/mixed, tax kind), money-in entries typed by the user (per stream,
with optional costs), hours worked, goals, receipts, set-aside payments and record-keeping ticks. Streams can be linked
to creatorbiz-ledger.json (creator income) or a "sales" list in digitalproducts.json; those files are only ever read.
Everything is the user's own numbers: nothing is fetched, filed or sent, and nothing here promises income.
UK tax notes are general information only: check GOV.UK for the current rules.
"""

from datetime import date

import homestore as hs
import memory
import screen
from config import Settings

FILE = "incomestreams.json"
FOLDER = "Income streams"
TYPES = ["active", "passive", "mixed"]
WEIGHT = {"active": 0.0, "mixed": 0.5, "passive": 1.0}
TAX_KINDS = ["trading", "property", "interest", "other"]
STATUSES = ["active", "paused", "ended"]
SECTIONS = {"streams": [], "entries": [], "hours": [], "goals": [], "receipts": [], "setaside": [], "records": {},
            "settings": {}, "next_id": 1}
NOTE = "General information only, not tax advice. Check GOV.UK for the current rules."
HONEST = "Only your own logged numbers; nothing here is a promise of future income."
ALLOWANCE = 1000
DEFAULT_SETASIDE = 20
LINKS = ["creatorbiz", "digitalproducts"]
MAX_ROWS = 3000
DASH_KIND = "incomestreams-dashboard"
BARS_KIND = "incomestreams-bars"
screen.EXTRA_KINDS.update({DASH_KIND, BARS_KIND})


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    data = {k: found[k] if isinstance(found.get(k), type(v)) else type(v)() for k, v in SECTIONS.items()}
    data["next_id"] = data["next_id"] or 1
    return data


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
    return f"Ask the user to confirm removing {what}. Only after a yes, call again with confirmed true."


def gbp(n: float) -> str:
    n = round(float(n), 2)
    return f"£{n:,.0f}" if n == int(n) else f"£{n:,.2f}"


def money(value, what: str = "amount", allow_zero: bool = False) -> float:
    text = str(value if value is not None else "").replace("£", "").replace(",", "").strip()
    try:
        n = round(float(text), 2)
    except ValueError:
        raise ValueError(f"Give the {what} as a number of pounds.") from None
    if n < 0 or (n == 0 and not allow_zero) or n > 10_000_000:
        raise ValueError(f"That {what} doesn't look right.")
    return n


# ---- Months and tax years -------------------------------------------------------------------------------

def month_of(day: date) -> str:
    return f"{day.year}-{day.month:02d}"


def add_months(key: str, n: int) -> str:
    y, m = int(key[:4]), int(key[5:7])
    total = y * 12 + (m - 1) + n
    return f"{total // 12}-{total % 12 + 1:02d}"


def months_back(count: int, end: str | None = None) -> list[str]:
    end = end or month_of(hs.today())
    return [add_months(end, -i) for i in range(count - 1, -1, -1)]


def parse_month(value) -> str:
    text = hs.clean(value).lower()
    if not text or text in ("this month", "current"):
        return month_of(hs.today())
    if text == "last month":
        return add_months(month_of(hs.today()), -1)
    try:
        d = date.fromisoformat(text[:7] + "-01")
    except ValueError:
        raise ValueError("Give the month as YYYY-MM, for example 2026-09.") from None
    return month_of(d)


def month_label(key: str) -> str:
    return date(int(key[:4]), int(key[5:7]), 1).strftime("%b %y")


def month_long(key: str) -> str:
    return date(int(key[:4]), int(key[5:7]), 1).strftime("%B %Y")


def entry_date(args: dict) -> date:
    """The date of a money-in entry: an exact date, or a month (today when it is this month, else the 15th)."""
    if args.get("date"):
        return hs.parse_day(args["date"])
    if args.get("month"):
        key = parse_month(args["month"])
        return hs.today() if key == month_of(hs.today()) else date(int(key[:4]), int(key[5:7]), 15)
    return hs.today()


def tax_start(day: date) -> int:
    return day.year if (day.month, day.day) >= (4, 6) else day.year - 1


def tax_range(start_year: int) -> tuple[date, date]:
    return date(start_year, 4, 6), date(start_year + 1, 4, 5)


def tax_label(start_year: int) -> str:
    return f"{start_year}/{str(start_year + 1)[2:]}"


def pick_tax_year(args: dict) -> int:
    n = args.get("tax_year_start")
    year = int(n) if n else tax_start(hs.today())
    if not 2000 <= year <= 2100:
        raise ValueError("Give the year the tax year starts, for example 2026 for 2026/27.")
    return year


# ---- Streams and entries --------------------------------------------------------------------------------

def stream(data: dict, value, what: str = "stream") -> dict:
    if isinstance(value, int) or str(value or "").strip().isdigit():
        n = int(str(value).strip())
        row = next((s for s in data["streams"] if s["id"] == n), None)
        if row:
            return row
    names = {s["name"]: s for s in data["streams"]}
    found = hs.find(names, hs.need(value, what))
    if found is None:
        raise ValueError(f"I can't find a stream called {hs.clean(value)}. Ask me to list your income streams.")
    return names[found]


def by_id(rows: list, value, what: str) -> dict:
    n = int(hs.number(value, f"{what} number", 1, 10_000_000))
    row = next((r for r in rows if r["id"] == n), None)
    if row is None:
        raise ValueError(f"I don't have {what} number {n}.")
    return row


def _read_linked(settings: Settings, s: dict) -> list[dict]:
    found = []
    if s.get("link") == "creatorbiz":
        cat = hs.clean(s.get("link_category")).lower()
        for e in hs.load(settings, "creatorbiz-ledger.json", []):
            if isinstance(e, dict) and e.get("kind") == "income" and (not cat or str(e.get("category", "")).lower() == cat):
                found.append((e.get("date"), e.get("amount"), e.get("note") or e.get("brand") or ""))
    elif s.get("link") == "digitalproducts":
        sales = hs.load(settings, "digitalproducts.json", {}).get("sales")
        for e in sales if isinstance(sales, list) else []:
            if isinstance(e, dict):
                found.append((e.get("date"), e.get("amount", e.get("price")), e.get("product") or e.get("note") or ""))
    rows = []
    for day, amount, note in found:
        try:
            d = date.fromisoformat(str(day)[:10])
            amt = round(float(amount), 2)
        except (TypeError, ValueError):
            continue
        if amt > 0:
            rows.append({"id": None, "stream": s["id"], "date": d.isoformat(), "month": month_of(d), "amount": amt,
                         "costs": 0.0, "note": hs.clean(note, 80), "source": s["link"]})
    return rows


def entries(settings: Settings, data: dict) -> list[dict]:
    """Typed entries plus read-only linked ones, each with a month."""
    rows = [dict(e, month=str(e["date"])[:7], source="typed") for e in data["entries"]]
    for s in data["streams"]:
        if s.get("link"):
            rows += _read_linked(settings, s)
    return rows


def total(rows: list[dict], sid=None, months=None, since: str = "", until: str = "", field: str = "amount") -> float:
    n = 0.0
    for e in rows:
        if sid is not None and e["stream"] != sid:
            continue
        if months is not None and e["month"] not in months:
            continue
        if (since and e["date"] < since) or (until and e["date"] > until):
            continue
        n += e[field]
    return round(n, 2)


def hours_total(data: dict, sid: int, months=None) -> float:
    return round(sum(h["hours"] for h in data["hours"] if h["stream"] == sid and (months is None or h["month"] in months)), 2)


def name_of(data: dict, sid: int) -> str:
    return next((s["name"] for s in data["streams"] if s["id"] == sid), "removed stream")


def need_streams(data: dict) -> None:
    if not data["streams"]:
        raise ValueError("You haven't added any income streams yet. Tell me one, for example: add an income stream called "
                         "Etsy prints, mostly active.")


def type_word(t: str) -> str:
    return {"active": "active", "passive": "passive-ish", "mixed": "part active, part passive"}.get(t, t)


def folder(settings: Settings):
    p = memory.root(settings) / FOLDER
    p.mkdir(parents=True, exist_ok=True)
    return p


def bars_card(title: str, card_id: str, rows: list[dict], note: str = "", buttons=None) -> dict:
    """Progress bars: rows of {label, value, max, text, say, warn}."""
    clean_rows = [{"label": hs.clean(r["label"], 60), "value": round(float(r["value"]), 2), "max": round(float(r["max"]), 2),
                   "text": hs.clean(r.get("text"), 80), "say": hs.clean(r.get("say"), 200), "warn": bool(r.get("warn"))}
                  for r in rows[:20]]
    return screen.card(BARS_KIND, title, card_id, data={"rows": clean_rows, "note": hs.clean(note, 300)}, buttons=buttons)
