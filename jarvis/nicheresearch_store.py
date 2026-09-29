"""Shared bits for the niche-research abilities: choosing and testing a niche or business idea before spending money.

Everything is in nicheresearch.json in the memory folder (niches with ratings, persona, pain points, competitors, prices
seen, SWOT, canvas, experiments and a lessons journal). Files you ask for are saved in the "Niche research" folder.
All ratings and notes are typed by you; nothing here measures a real market, and nothing is posted or sent anywhere.
"""

import re
from pathlib import Path

import memory
import screen
from config import Settings
from creatorbiz_store import clean, find, gbp, load, need, parse_date, save, short, today  # noqa: F401 (re-exported)

FILE = "nicheresearch.json"
FOLDER = "Niche research"
MAX_ROWS = 300
HONEST = "These are your own ratings and notes, a thinking aid rather than proof. Test with real people before spending money."

CRITERIA = {
    "demand": "How many people clearly want this? 5 = plenty, 1 = hardly anyone",
    "competition": "Room to stand out. 5 = little competition or an easy angle, 1 = crowded and dominated",
    "passion": "How much you enjoy the topic. 5 = could talk about it for years, 1 = a chore",
    "skill": "How well you can deliver already. 5 = strong skills, 1 = starting from nothing",
    "profit": "Money potential. 5 = people already pay well, 1 = few pay",
    "evergreen": "Lasting interest. 5 = stays useful for years, 1 = a passing trend",
}
DEFAULT_WEIGHTS = {"demand": 3, "competition": 2, "passion": 2, "skill": 2, "profit": 3, "evergreen": 1}

SHEET, RADAR, SWOT, CHECK, BOARD = ("nicheresearch-sheet", "nicheresearch-radar", "nicheresearch-swot",
                                    "nicheresearch-check", "nicheresearch-board")
screen.EXTRA_KINDS.update({SHEET, RADAR, SWOT, CHECK, BOARD})


def number(value, what: str, low: float = 0, high: float = 100_000_000) -> float:
    try:
        n = float(str(value if value is not None else "").replace("£", "").replace(",", "").replace("%", "").strip())
    except ValueError:
        raise ValueError(f"Give the {what} as a number.") from None
    if n < low or n > high:
        raise ValueError(f"That {what} should be between {low:g} and {high:g}.")
    return n


def rating(value, what: str) -> int:
    return int(number(value, what, 1, 5))


def next_id(rows: list[dict]) -> int:
    return max([r.get("id", 0) for r in rows] + [0]) + 1


def pick(rows: list[dict], ref, field: str, what: str) -> dict:
    """A row by number or by (part of) its name field."""
    text = clean(ref)
    if not text:
        raise ValueError(f"Which {what}? Give its number or name.")
    if text.lstrip("#").isdigit():
        hit = next((r for r in rows if r["id"] == int(text.lstrip("#"))), None)
        if hit:
            return hit
    key = find([r[field] for r in rows], text)
    hit = next((r for r in rows if r[field] == key), None)
    if hit is None:
        raise ValueError(f"I can't find a {what} called {text}. Say its number or exact name.")
    return hit


def data(settings: Settings) -> dict:
    d = load(settings, FILE, {})
    if not isinstance(d.get("niches"), list):
        d["niches"] = []
    if not isinstance(d.get("journal"), list):
        d["journal"] = []
    if not isinstance(d.get("weights"), dict):
        d["weights"] = {}
    return d


def weights(d: dict) -> dict:
    return {k: d["weights"].get(k, v) for k, v in DEFAULT_WEIGHTS.items()}


def new_niche(name: str, note: str = "") -> dict:
    return {"name": name, "note": note, "ratings": {}, "persona": {}, "pains": [], "competitors": [], "prices": [],
            "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}, "canvas": {}, "positioning": {},
            "experiments": [], "smoke": [], "decision": {}, "survey": [], "my_topics": [], "gaps": [], "created": today().isoformat()}


def open_data(settings: Settings) -> dict:
    """The saved data with every missing niche field filled in."""
    d = data(settings)
    for n in d["niches"]:
        for key, default in new_niche(n["name"]).items():
            n.setdefault(key, default)
    return d


def niche(d: dict, args: dict, key: str = "niche") -> dict:
    """The niche named in args, or the only one there is."""
    if not d["niches"]:
        raise ValueError("No niches yet. Say the name of a niche or idea to add one.")
    if not clean(args.get(key)):
        if len(d["niches"]) == 1:
            return d["niches"][0]
        raise ValueError("Which niche? " + ", ".join(n["name"] for n in d["niches"]))
    return pick(d["niches"], args.get(key), "name", "niche")


def open_niche(settings: Settings, args: dict):
    d = open_data(settings)
    return d, niche(d, args)


def weighted(n: dict, w: dict):
    """Weighted score out of 100, or None until every criterion is rated."""
    r = n["ratings"]
    if any(k not in r for k in CRITERIA):
        return None
    return round(sum(r[k] * w[k] for k in CRITERIA) / (5 * sum(w.values())) * 100)


def band(score: int) -> str:
    for floor, word in ((80, "strong candidate"), (65, "promising"), (50, "worth testing carefully"), (35, "risky")):
        if score >= floor:
            return word
    return "weak fit for now"


def items(value) -> list[str]:
    """A list from text split on commas, semicolons or new lines (or from a list)."""
    raw = value if isinstance(value, list) else re.split(r"[\n;,]+", str(value or ""))
    return [clean(x, 120) for x in raw if clean(x)]


def dispatch(handlers: dict, settings: Settings, args: dict):
    action = args.get("action")
    if action not in handlers:
        raise ValueError("Which action? " + ", ".join(handlers))
    return handlers[action](settings, args)


def confirm_first(args: dict, what: str):
    return None if args.get("confirmed") is True else f"That deletes {what}. Say yes to confirm."


def write_file(settings: Settings, name: str, text: str) -> Path:
    folder = memory.root(settings) / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = memory.unique_path(folder / memory.safe_name(name, "file name"))
    path.write_text(text, encoding="utf-8")
    return path


# ---- pop-up cards -----------------------------------------------------------------------------------------------------

def sheet(text: str, title: str, sections, note: str = "", buttons=None, headline: str = "") -> screen.Shown:
    """sections: (heading, [lines]) where a line is text or (text, say)."""
    def line(x):
        return {"text": str(x[0]), "say": str(x[1])} if isinstance(x, tuple) else {"text": str(x), "say": ""}
    return screen.Shown(text, screen.card(SHEET, title, "", buttons=buttons, data={
        "headline": headline, "note": note, "sections": [{"heading": h, "lines": [line(x) for x in lines]} for h, lines in sections]}))


def check(text: str, title: str, headline: str, rows, note: str = "", buttons=None) -> screen.Shown:
    """rows: (label, status ok/warn/fail/todo, detail, say)."""
    return screen.Shown(text, screen.card(CHECK, title, "", buttons=buttons, data={
        "headline": headline, "note": note,
        "items": [{"label": str(a), "status": b if b in ("ok", "warn", "fail", "todo") else "todo", "detail": str(c), "say": str(e)}
                  for a, b, c, e in rows]}))


def board(text: str, title: str, columns, note: str = "", buttons=None) -> screen.Shown:
    """columns: (heading, [(label, small text, say line)])."""
    return screen.Shown(text, screen.card(BOARD, title, "", buttons=buttons, data={
        "columns": [{"title": h, "cards": [{"label": str(a), "small": str(b), "say": str(c)} for a, b, c in cards]}
                    for h, cards in columns], "note": note}))


def table(text: str, title: str, columns, rows) -> screen.Shown:
    return screen.Shown(text, screen.card("table", title, "", columns=columns, rows=rows))


def tappable(text: str, title: str, rows) -> screen.Shown:
    """A list where each row is (label, say line)."""
    return screen.Shown(text, screen.card("list", title, "", items=[{"label": a, "say": b} for a, b in rows]))
