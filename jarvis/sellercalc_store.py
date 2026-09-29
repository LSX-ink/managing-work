"""Shared bits for the seller calculators: the one dated fee table, fee and profit maths, postage bands and stock log.

Files in the memory folder: sellercalc-settings.json (your fee overrides and edited postage bands),
sellercalc-inventory.json, sellercalc-returns.json, sellercalc-sources.json and sellercalc-drafts.json. Everything stays
on this PC; nothing is posted and no marketplace is contacted. Fees change often: the table is approximate and dated.
"""

from datetime import date

import screen
from config import Settings
from creatorbiz_store import clean, find, gbp, load, need, parse_date, save, short, today  # noqa: F401 (re-exported)

FEES_CHECKED = "2026-09"  # month the rates below were last looked over; platforms change them without warning
SETTINGS = "sellercalc-settings.json"
INVENTORY = "sellercalc-inventory.json"
RETURNS = "sellercalc-returns.json"
SOURCES = "sellercalc-sources.json"
DRAFTS = "sellercalc-drafts.json"
MAX_ROWS = 3000
HONEST = ("Fees change, so check the platform's own fee page before you rely on these. They are estimates, "
          "not financial or tax advice.")

RESULT, COMPARE, FEES, BARS, GUIDE = ("sellercalc-result", "sellercalc-compare", "sellercalc-fees", "sellercalc-bars",
                                      "sellercalc-guide")
screen.EXTRA_KINDS.update({RESULT, COMPARE, FEES, BARS, GUIDE})

# pct and fixed are what the seller pays per sale; on_ship means the percentage also applies to postage the buyer pays.
# buyer_ship: the buyer pays the carrier directly (Vinted); local: pick-up, no postage. handling: fulfilment cost (FBA).
PLATFORMS = {
    "etsy": {"name": "Etsy", "pct": 10.5, "fixed": 0.36, "on_ship": True,
             "note": "About 6.5% transaction fee + 4% payment fee, plus 20p payment and 16p listing. Offsite ads cost extra "
                     "(roughly 12 to 15%) only when a sale came from them; add that with extra_pct."},
    "ebay_private": {"name": "eBay (private seller)", "pct": 0, "fixed": 0, "on_ship": True,
                     "note": "Private sellers pay no selling fee on most items. Optional extras (promoted listings) and some "
                             "categories can still cost money. Regular selling for profit may make you a trader."},
    "ebay_business": {"name": "eBay (business seller)", "pct": 12.8, "fixed": 0.30, "on_ship": True, "small_limit": 10,
                      "small_fixed": 0.10,
                      "note": "About 12.8% final value fee on most categories (charged on item + postage) plus 30p an order "
                              "(10p if the order is £10 or under). Categories differ; shop owners get lower rates."},
    "vinted": {"name": "Vinted", "pct": 0, "fixed": 0, "on_ship": False, "buyer_ship": True, "buyer_pct": 5,
               "buyer_fixed": 0.70,
               "note": "Sellers pay nothing to sell on Vinted. The buyer pays a Buyer Protection fee (about 5% + 70p) on top "
                       "of the price, and the buyer pays postage to the carrier. Business sellers should check Vinted's rules."},
    "depop": {"name": "Depop", "pct": 2.9, "fixed": 0.30, "on_ship": True,
              "note": "Depop UK has moved away from a selling fee; payment processing is about 2.9% + 30p. Depop changes its "
                      "fees often, so check."},
    "amazon_fbm": {"name": "Amazon (you post, FBM)", "pct": 15, "fixed": 0.75, "on_ship": True,
                   "note": "Referral fee about 15% for most categories (8% for some, higher for others). The Individual plan "
                           "charges about 75p an item; the Professional plan charges about £25 a month and no per-item fee."},
    "amazon_fba": {"name": "Amazon FBA", "pct": 15, "fixed": 0.75, "on_ship": True, "handling": 3.50,
                   "note": "Same referral fee, plus Amazon's fulfilment fee (roughly £2 to £7 for small and standard items) "
                           "and storage fees. The handling figure here is a rough middle guess: edit it for your item."},
    "facebook_local": {"name": "Facebook Marketplace (pick-up)", "pct": 0, "fixed": 0, "on_ship": False, "local": True,
                       "note": "Local pick-up sales are free. Cash or bank transfer means no fee, but no seller protection either."},
    "facebook_shipped": {"name": "Facebook Marketplace (shipped)", "pct": 10, "fixed": 0, "on_ship": True, "min_fee": 0.80,
                         "note": "Shipped orders paid through Facebook cost about 10% with a small minimum. Availability in the "
                                 "UK varies, so check."},
    "own_shop": {"name": "Own shop (Shopify-style)", "pct": 2.2, "fixed": 0.20, "on_ship": True,
                 "note": "Card fees about 2.2% + 20p on UK cards (more for international cards). The shop plan is a separate "
                         "monthly cost, around £20 to £30: use the shop_monthly action to include it."},
}
ALIASES = {"ebay": "ebay_private", "ebay private": "ebay_private", "ebay business": "ebay_business",
           "ebay trader": "ebay_business", "amazon": "amazon_fbm", "fbm": "amazon_fbm", "fba": "amazon_fba",
           "facebook": "facebook_local", "facebook marketplace": "facebook_local", "marketplace": "facebook_local",
           "facebook shipped": "facebook_shipped", "shopify": "own_shop", "own shop": "own_shop", "shop": "own_shop",
           "website": "own_shop", "gumtree": "facebook_local"}

# Approximate UK postage bands (max weight, longest side, price). Edit them with postage_set; check the carrier's site.
POSTAGE = [
    {"id": "rm_large_letter", "name": "Royal Mail Large Letter (2nd class)", "max_g": 750, "max_cm": 35, "price": 1.75},
    {"id": "evri_small", "name": "Evri small parcel", "max_g": 1000, "max_cm": 45, "price": 2.85},
    {"id": "rm_small_parcel", "name": "Royal Mail Small Parcel (2nd class)", "max_g": 2000, "max_cm": 45, "price": 3.95},
    {"id": "evri_medium", "name": "Evri medium parcel", "max_g": 5000, "max_cm": 80, "price": 3.99},
    {"id": "rm_medium_parcel", "name": "Royal Mail Medium Parcel (2nd class)", "max_g": 20000, "max_cm": 61, "price": 6.99},
    {"id": "evri_large", "name": "Evri large parcel", "max_g": 15000, "max_cm": 120, "price": 6.49},
]
POSTAGE_NOTE = ("Postage prices here are approximate and go out of date. Check royalmail.com or evri.com, "
                "and edit the table so it matches what you really pay.")


def number(value, what: str, allow_zero: bool = False, top: float = 1_000_000) -> float:
    try:
        n = float(str(value if value is not None else "").replace("£", "").replace(",", "").replace("%", "").strip())
    except ValueError:
        raise ValueError(f"Give the {what} as a number.") from None
    if n < 0 or (n == 0 and not allow_zero) or n > top:
        raise ValueError(f"That {what} doesn't look right.")
    return round(n, 2)


def arg(args: dict, key: str, what: str, zero: bool = False, default=None, top: float = 1_000_000) -> float:
    if args.get(key) is None or args.get(key) == "":
        if default is not None:
            return default
        raise ValueError(f"Tell me the {what}.")
    return number(args[key], what, allow_zero=zero, top=top)


def num(n: float) -> str:
    return f"{n:g}" if abs(n * 10 - round(n * 10)) < 1e-9 else f"{n:.2f}"


def pct_text(n: float) -> str:
    return f"{n:g}%"


def result(text: str, title: str, headline: str, sub: str = "", rows=None, notes=None, buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card(RESULT, title, "", buttons=buttons, data={
        "headline": headline, "sub": sub, "rows": [[str(a), str(b)] for a, b in (rows or [])], "notes": list(notes or [])}))


def guide(text: str, title: str, sections, note: str = "", buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card(GUIDE, title, "", buttons=buttons, data={
        "sections": [{"heading": h, "lines": [str(x) for x in lines]} for h, lines in sections], "note": note}))


def bars(text: str, title: str, rows, note: str = "", buttons=None) -> screen.Shown:
    """rows: (label, value text, share 0-100, small text)."""
    return screen.Shown(text, screen.card(BARS, title, "", buttons=buttons, data={
        "rows": [{"label": str(a), "value": str(b), "pct": max(0, min(100, float(c))), "small": str(d)} for a, b, c, d in rows],
        "note": note}))


# ---- settings, fee table --------------------------------------------------------------------------------------------

def user_settings(settings: Settings) -> dict:
    return load(settings, SETTINGS, {})


def rates(settings: Settings) -> dict:
    """The fee table with any of your own overrides on top, each row marked with what you changed."""
    mine = user_settings(settings).get("rates", {})
    out = {}
    for key, row in PLATFORMS.items():
        merged = dict(row)
        over = mine.get(key) if isinstance(mine.get(key), dict) else {}
        merged.update({k: v for k, v in over.items() if k in ("pct", "fixed", "handling")})
        merged["key"], merged["mine"] = key, sorted(k for k in over if k in ("pct", "fixed", "handling"))
        out[key] = merged
    return out


def platform(settings: Settings, name) -> dict:
    text = clean(name).lower().replace("-", " ").replace("_", " ")
    table = rates(settings)
    if not text:
        raise ValueError("Which platform? Etsy, eBay, Vinted, Depop, Amazon, Facebook Marketplace or your own shop.")
    if text.replace(" ", "_") in table:
        return table[text.replace(" ", "_")]
    if text in ALIASES:
        return table[ALIASES[text]]
    hits = [r for r in table.values() if text in r["name"].lower()]
    if len(hits) == 1:
        return hits[0]
    if hits:
        raise ValueError(f"Which {clean(name)}? " + " or ".join(h["name"] for h in hits[:3]) + ".")
    raise ValueError(f"I don't have fees for {clean(name)}. Try: " + ", ".join(r["name"] for r in table.values()) + ".")


def fee_of(rate: dict, price: float, ship: float = 0.0, extra_pct: float = 0.0) -> float:
    base = price + (ship if rate.get("on_ship") else 0.0)
    fixed = rate.get("fixed", 0.0)
    if rate.get("small_limit") and base <= rate["small_limit"]:
        fixed = rate.get("small_fixed", fixed)
    fee = base * (rate.get("pct", 0.0) + extra_pct) / 100 + fixed
    if fee and rate.get("min_fee"):
        fee = max(fee, rate["min_fee"])
    return round(fee, 2)


def profit_on(rate: dict, price: float, cost: float = 0.0, ship_charged: float = 0.0, ship_cost: float = 0.0,
              packaging: float = 0.0, extra_pct: float = 0.0) -> dict:
    """Net profit on one sale. Local and buyer-pays-carrier platforms ignore postage; FBA swaps it for the handling fee."""
    if rate.get("local") or rate.get("buyer_ship"):
        ship_charged = ship_cost = 0.0
    if rate.get("handling") is not None:
        ship_cost = rate["handling"]
    fee = fee_of(rate, price, ship_charged, extra_pct)
    income = price + ship_charged
    net = round(income - fee - cost - ship_cost - packaging, 2)
    return {"income": round(income, 2), "fee": fee, "ship_cost": round(ship_cost, 2), "ship_charged": round(ship_charged, 2),
            "cost": cost, "packaging": packaging, "net": net,
            "margin": round(100 * net / income, 1) if income else 0.0,
            "roi": round(100 * net / (cost + packaging), 1) if cost + packaging else None}


def solve_price(rate: dict, target: float = 0.0, margin_pct: float | None = None, cost: float = 0.0, ship_charged: float = 0.0,
                ship_cost: float = 0.0, packaging: float = 0.0, extra_pct: float = 0.0) -> float:
    """The lowest price (to the penny) whose net profit reaches the target profit, or the target margin on the sale."""
    def enough(pence: int) -> bool:
        p = profit_on(rate, pence / 100, cost, ship_charged, ship_cost, packaging, extra_pct)
        if margin_pct is not None:
            return p["income"] > 0 and p["net"] >= p["income"] * margin_pct / 100 - 1e-9
        return p["net"] >= target - 1e-9

    lo, hi = 1, 100_000_000
    if not enough(hi):
        raise ValueError("The fees would swallow that; a margin that high isn't possible.")
    while lo < hi:
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if enough(mid) else (mid + 1, hi)
    return lo / 100


def fee_line(rate: dict) -> str:
    parts = []
    if rate.get("pct"):
        parts.append(pct_text(rate["pct"]))
    if rate.get("fixed"):
        parts.append(gbp(rate["fixed"]))
    if rate.get("handling") is not None:
        parts.append(f"{gbp(rate['handling'])} fulfilment")
    return " + ".join(parts) if parts else "no seller fee"


# ---- postage --------------------------------------------------------------------------------------------------------

def postage_bands(settings: Settings) -> list[dict]:
    mine = user_settings(settings).get("postage")
    if isinstance(mine, list) and mine:
        return [b for b in mine if isinstance(b, dict) and b.get("price") is not None]
    return [dict(b) for b in POSTAGE]


# ---- stock log ------------------------------------------------------------------------------------------------------

def items(settings: Settings) -> list[dict]:
    return [i for i in load(settings, INVENTORY, []) if isinstance(i, dict)]


def save_items(settings: Settings, rows: list[dict]) -> None:
    save(settings, INVENTORY, rows)


def pick_item(rows: list[dict], ref) -> dict:
    text = clean(ref)
    if not text:
        raise ValueError("Which item? Give its number or name.")
    digits = text.lstrip("#")
    if digits.isdigit():
        hit = next((i for i in rows if i["id"] == int(digits)), None)
        if hit:
            return hit
    key = find([i["name"] for i in rows], text)
    hit = next((i for i in rows if i["name"] == key), None)
    if hit is None:
        raise ValueError(f"I can't find an item called {text}. Say its number or exact name.")
    return hit


def day_of(value) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def is_sold(item: dict) -> bool:
    return item.get("status") == "sold"


def item_profit(item: dict) -> float:
    return round(float(item.get("sold_for", 0)) + float(item.get("postage_charged", 0)) - float(item.get("fees", 0))
                 - float(item.get("postage", 0)) - float(item.get("other_costs", 0)) - float(item.get("bought_for", 0)), 2)


def days_to_sell(item: dict) -> int | None:
    end = day_of(item.get("sold_date"))
    start = day_of(item.get("listed_date")) or day_of(item.get("bought_date"))
    return max((end - start).days, 0) if end and start else None


def days_held(item: dict, ref: date | None = None) -> int:
    start = day_of(item.get("bought_date")) or day_of(item.get("listed_date")) or (ref or today())
    return max(((ref or today()) - start).days, 0)
