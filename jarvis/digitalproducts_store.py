"""Shared bits for the digital products abilities: digitalproducts.json plus generated files in the memory folder.

Ideas, products (idea, making, listed, retired), listing drafts, customer FAQ, bundles, launch checklists, price
comparisons and version logs live in the JSON file. Products made by Alfred are files in digitalproducts/:
printable HTML (print to PDF from the browser), simple PDFs, Markdown, CSV and PNG. It is making, writing and
tracking only: nothing is uploaded, sold or posted, and nothing leaves the PC.
"""

import html
import re
from pathlib import Path

import homestore as hs
import memory
import screen
from config import Settings

FILE = "digitalproducts.json"
FOLDER = "digitalproducts"
MAX_ITEMS = 500
STATUSES = ["idea", "making", "listed", "retired"]
FORMATS = ["ebook", "printable planner", "checklist", "template", "worksheet", "prompt pack", "guide",
           "course outline", "wallpaper pack", "habit tracker", "budget sheet", "spreadsheet"]
SECTIONS = {"ideas": [], "products": [], "listings": {}, "faq": [], "bundles": [], "launch": {}, "comps": [],
            "versions": [], "next_id": 1}
PRICE_NOTE = "Check what similar products sell for before settling on a price; nothing here is a guaranteed result."


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    data = {k: found[k] if isinstance(found.get(k), type(v)) else type(v)() for k, v in SECTIONS.items()}
    data["next_id"] = data["next_id"] or 1
    return data


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def folder(settings: Settings, sub: str = "") -> Path:
    p = memory.root(settings) / FOLDER / sub if sub else memory.root(settings) / FOLDER
    p.mkdir(parents=True, exist_ok=True)
    return p


def put(rows: list, item, limit: int = MAX_ITEMS) -> None:
    if len(rows) >= limit:
        raise ValueError("That list is full; remove something first.")
    rows.append(item)


def new_id(data: dict) -> int:
    n = data["next_id"]
    data["next_id"] += 1
    return n


def confirm_needed(what: str) -> str:
    return f"Ask the user to confirm removing {what}. Only after a yes, call again with confirmed true."


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:50] or "product"


def by_id(rows: list, args: dict, what: str, key: str = "id") -> dict:
    n = int(hs.number(args.get(key), f"{what} number", 1, 1_000_000))
    row = next((r for r in rows if r["id"] == n), None)
    if row is None:
        raise ValueError(f"I don't have {what} number {n}. Ask me to show the list to see the numbers.")
    return row


def product(data: dict, args: dict, key: str = "product") -> dict:
    """A product by number or by name (a close name is fine)."""
    value = args.get(key) if args.get(key) is not None else args.get("id")
    if isinstance(value, int) or str(value or "").strip().isdigit():
        return by_id(data["products"], {"id": int(str(value).strip())}, "product")
    name = hs.need(value, "product")
    names = {p["name"]: p for p in data["products"]}
    found = hs.find(names, name)
    if found is None:
        raise ValueError(f"I can't find a product called {name}. Ask me to show the catalogue.")
    return names[found]


def text_list(value, limit: int = 40, size: int = 120) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[\n;]|,(?!\d)", value)
    return [hs.clean(v, size) for v in (value or []) if hs.clean(v, size)][:limit]


def gbp(n: float) -> str:
    return f"£{n:,.2f}"


# ---- Printable pages: one list of blocks becomes HTML (print to PDF) and Markdown (simple PDF) ----------

CSS = ("@page{size:A4;margin:14mm}body{font:14px/1.5 Arial,sans-serif;color:#000;background:#fff;margin:0 auto;"
       "max-width:190mm}h1{font-size:26px;margin:0 0 6px}h2{font-size:18px;margin:18px 0 6px}"
       ".p{margin:4px 0}.ck{margin:6px 0}.ck:before{content:'\\2610  '}.ln{border-bottom:1px solid #000;height:26px}"
       "table{border-collapse:collapse;width:100%;margin:8px 0;font-size:12px}td,th{border:1px solid #000;"
       "padding:6px;text-align:left;height:22px}th{background:#eee}.box{border:1px solid #000;min-height:90px;"
       "padding:6px;margin:6px 0}.pb{page-break-after:always}@media print{.hint{display:none}}")


def _cell(v) -> str:
    return html.escape(str(v))


def blocks_html(blocks: list, title: str) -> str:
    out = ['<p class="hint">Print this page (Ctrl+P) and choose Save as PDF.</p>']
    for b in blocks:
        kind = b[0]
        if kind in ("h1", "h2"):
            out.append(f"<{kind}>{_cell(b[1])}</{kind}>")
        elif kind == "p":
            out.append(f'<p class="p">{_cell(b[1])}</p>')
        elif kind == "check":
            out.append(f'<div class="ck">{_cell(b[1])}</div>')
        elif kind == "lines":
            out.append('<div class="ln"></div>' * b[1])
        elif kind == "box":
            out.append(f'<div class="box"><b>{_cell(b[1])}</b></div>')
        elif kind == "bullets":
            out.append("<ul>" + "".join(f"<li>{_cell(i)}</li>" for i in b[1]) + "</ul>")
        elif kind == "table":
            head = "".join(f"<th>{_cell(h)}</th>" for h in b[1])
            rows = "".join("<tr>" + "".join(f"<td>{_cell(c)}</td>" for c in r) + "</tr>" for r in b[2])
            out.append(f"<table><tr>{head}</tr>{rows}</table>")
        elif kind == "pagebreak":
            out.append('<div class="pb"></div>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{_cell(title)}</title>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head>'
            f"<body>{''.join(out)}</body></html>")


def blocks_md(blocks: list) -> str:
    out = []
    for b in blocks:
        kind = b[0]
        if kind in ("h1", "h2"):
            out.append(("# " if kind == "h1" else "## ") + b[1])
        elif kind == "p":
            out.append(b[1])
        elif kind == "check":
            out.append(f"- [ ] {b[1]}")
        elif kind == "lines":
            out.append("\n\n".join("_" * 60 for _ in range(min(b[1], 12))))
        elif kind == "box":
            out.append(f"**{b[1]}**\n\n" + "_" * 60)
        elif kind == "bullets":
            out.append("\n".join(f"- {i}" for i in b[1]))
        elif kind == "table":
            rows = [b[1]] + list(b[2])[:40]
            out.append("\n".join("- " + " | ".join(str(c) for c in r if str(c) != "") for r in rows))
        elif kind == "pagebreak":
            out.append("---")
    return "\n\n".join(out) + "\n"


def unique(where: Path, name: str, ext: str) -> Path:
    base = slug(name)
    p, n = where / f"{base}{ext}", 2
    while p.exists():
        p, n = where / f"{base}-{n}{ext}", n + 1
    return p


def shown_file(settings: Settings, path: Path, text: str) -> screen.Shown:
    if path.suffix == ".html":
        buttons = [{"label": "Make a PDF", "say": f"Make a PDF of the digital product file {path.name}."}]
    else:
        buttons = [{"label": "All my files", "say": "Show my digital product files."}]
    return screen.Shown(text, screen.file_card(settings, path, buttons))
