"""Shared bits for the Kinetic Web Designs business tools (kinetic_find, kinetic_sales, kinetic_invoices).

Data lives in the memory folder: kinetic-prospects.json (businesses found and their website audits), kinetic-prices.json
(your package prices), kinetic-business.json (your business details for quotes and invoices), kinetic-quotes.json and
kinetic-invoices.json. Documents are saved under the "Kinetic Web Designs" memory folder, in Prospects, Audits,
Mockups and Clients/<client>. Nothing here sends an email, posts anything or takes a payment: every message is a draft
the user sends themselves.
"""

import re
from pathlib import Path

import memory
import screen
from config import Settings
from creatorbiz_store import clean, gbp, load, long_date, need, parse_date, save, short, today  # noqa: F401 (re-exported)

FOLDER = "Kinetic Web Designs"
PROSPECTS = "kinetic-prospects.json"
PRICES = "kinetic-prices.json"
BUSINESS = "kinetic-business.json"
QUOTES = "kinetic-quotes.json"
INVOICES = "kinetic-invoices.json"
MAX_ROWS = 2000
NOT_SENT = "Nothing has been sent; you send it yourself when you're happy with it."


def number(value, what: str, allow_zero: bool = False, top: float = 1_000_000) -> float:
    try:
        n = float(str(value if value is not None else "").replace("£", "").replace(",", "").replace("%", "").strip())
    except ValueError:
        raise ValueError(f"Give the {what} as a number.") from None
    if n < 0 or (n == 0 and not allow_zero) or n > top:
        raise ValueError(f"That {what} doesn't look right.")
    return round(n, 2)


def num(n: float) -> str:
    return f"{n:g}" if abs(n * 10 - round(n * 10)) < 1e-9 else f"{n:.2f}"


def rows_of(settings: Settings, name: str) -> list[dict]:
    return [r for r in load(settings, name, []) if isinstance(r, dict)]


def folder(settings: Settings, *parts: str) -> Path:
    """Kinetic Web Designs/<parts...> inside the memory folder, created if missing."""
    path = memory.root(settings) / FOLDER
    for part in parts:
        path = path / memory.safe_name(part, "folder name")
    path.mkdir(parents=True, exist_ok=True)
    return path


def write(settings: Settings, parts: tuple, name: str, text: str, replace: bool = False) -> Path:
    path = folder(settings, *parts) / memory.safe_name(name, "file name")
    if not replace:
        path = memory.unique_path(path)
    path.write_text(text, encoding="utf-8")
    return path


def file_shown(settings: Settings, path: Path, text: str, buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.file_card(settings, path, buttons))


def where(settings: Settings, path: Path) -> str:
    return path.relative_to(memory.root(settings)).as_posix()


def table(text: str, title: str, columns, rows, buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card("table", title, "", columns=columns, rows=rows, buttons=buttons))


def text_card(text: str, title: str, body: str, buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card("text", title, "", buttons=buttons, text=body))


def dispatch(handlers: dict, action, settings: Settings, args: dict, what: str):
    if action not in handlers:
        raise ValueError(f"Which {what} action? " + ", ".join(handlers))
    return handlers[action](settings, args)


def next_id(rows: list[dict]) -> int:
    return max([r.get("id", 0) for r in rows] + [0]) + 1


def business(settings: Settings) -> dict:
    found = load(settings, BUSINESS, {})
    return {"name": "Kinetic Web Designs", "owner": "", "email": "", "phone": "", "website": "", "address": "",
            "bank_name": "", "sort_code": "", "account_number": "", "vat_number": "", **found}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")


def domain(url: str) -> str:
    m = re.match(r"^(?:https?://)?(?:www\.)?([^/:?#]+)", str(url or "").strip().lower())
    return m.group(1) if m else ""


def find_prospect(rows: list[dict], name) -> dict | None:
    """A saved prospect by number, exact name, website domain or part of its name."""
    key = str(name or "").strip().lower()
    if not key:
        return None
    if key.isdigit():
        return next((r for r in rows if r.get("id") == int(key)), None)
    for test in (lambda r: r["name"].lower() == key, lambda r: domain(r.get("website", "")) == domain(key),
                 lambda r: key in r["name"].lower()):
        hits = [r for r in rows if test(r)]
        if hits:
            return hits[0]
    return None


STYLE = ("*{box-sizing:border-box}body{font-family:'Segoe UI',Arial,sans-serif;max-width:820px;margin:2em auto;"
         "padding:0 1.2em;color:#16181d;line-height:1.55}header{display:flex;justify-content:space-between;gap:1em;"
         "flex-wrap:wrap;border-bottom:3px solid #16181d;padding-bottom:1em;margin-bottom:1.5em}header h1{margin:0;"
         "font-size:1.6em;letter-spacing:.02em}header .me{text-align:right;font-size:.9em;color:#444}"
         "h2{font-size:1.15em;margin-top:1.8em;border-bottom:1px solid #ddd;padding-bottom:.3em}"
         "table{border-collapse:collapse;width:100%;margin:.6em 0}th,td{border-bottom:1px solid #e3e3e3;padding:8px 6px;"
         "text-align:left;vertical-align:top}td.n,th.n{text-align:right;white-space:nowrap}tr.total td{font-weight:700;"
         "border-top:2px solid #16181d;border-bottom:none}.meta{display:grid;grid-template-columns:repeat(auto-fit,"
         "minmax(160px,1fr));gap:.4em 1.5em;font-size:.95em}.meta b{display:block;font-size:.8em;color:#666;"
         "text-transform:uppercase;letter-spacing:.06em}.note{background:#f4f5f7;border-radius:8px;padding:.8em 1em}"
         "footer{margin-top:2.5em;font-size:.85em;color:#666}@media print{body{margin:0}}")


def doc_html(settings: Settings, title: str, body: str) -> str:
    """A printable document with the user's business details at the top. Save it as a PDF from the browser."""
    from html import escape
    me = business(settings)
    contact = "<br>".join(escape(x) for x in (me["owner"], me["address"], me["email"], me["phone"], me["website"]) if x)
    return (f"<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            f"content=\"width=device-width,initial-scale=1\"><title>{escape(title)}</title><style>{STYLE}</style>"
            f"</head><body>\n<header><h1>{escape(me['name'])}</h1><div class=\"me\">{contact}</div></header>\n"
            f"{body}\n</body></html>\n")
