"""Shared bits for the writing-income abilities: newsletter, blog, KDP book and paid-writing helpers.

Files in the memory folder: writingincome-newsletter.json, writingincome-blog.json, writingincome-books.json and
writingincome-pitches.json. Everything stays on this PC: nothing is posted, sent or looked up, and no platform is
contacted. All money figures are typed by you and are what-ifs, never a promise of income.
"""

import re

import screen
from config import Settings
from creatorbiz_store import clean, find, gbp, load, need, parse_date, save, short, today, until  # noqa: F401 (re-exported)

NEWSLETTER = "writingincome-newsletter.json"
BLOG = "writingincome-blog.json"
BOOKS = "writingincome-books.json"
PITCHES = "writingincome-pitches.json"
MAX_ROWS = 2000
HONEST = ("These are what-if sums from the numbers you typed, not a promise or forecast of income. "
          "Most writing earns little at first.")
TAX = "UK tax on writing income is general guidance only: check GOV.UK."

RESULT, GUIDE, CHECK, BOARD, METER = ("writingincome-result", "writingincome-guide", "writingincome-check",
                                      "writingincome-board", "writingincome-meter")
screen.EXTRA_KINDS.update({RESULT, GUIDE, CHECK, BOARD, METER})


def number(value, what: str, allow_zero: bool = False, top: float = 100_000_000) -> float:
    try:
        n = float(str(value if value is not None else "").replace("£", "").replace("$", "").replace(",", "").replace("%", "").strip())
    except ValueError:
        raise ValueError(f"Give the {what} as a number.") from None
    if n < 0 or (n == 0 and not allow_zero) or n > top:
        raise ValueError(f"That {what} doesn't look right.")
    return round(n, 4)


def arg(args: dict, key: str, what: str, zero: bool = False, default=None, top: float = 100_000_000) -> float:
    if args.get(key) is None or args.get(key) == "":
        if default is not None:
            return default
        raise ValueError(f"Tell me the {what}.")
    return number(args[key], what, allow_zero=zero, top=top)


def whole(args: dict, key: str, what: str, zero: bool = False, default=None, top: int = 100_000_000) -> int:
    return int(arg(args, key, what, zero, default, top))


def pounds(n: float) -> str:
    return f"-{gbp(abs(n))}" if n < 0 else gbp(n)


def day_arg(args: dict, key: str = "date"):
    return parse_date(args.get(key), key) or today()


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


def confirm_first(args: dict, what: str):
    """None when the user has confirmed, else the question to ask."""
    return None if args.get("confirmed") is True else f"That deletes {what}. Say yes to confirm."


def dispatch(handlers: dict, settings: Settings, args: dict):
    action = args.get("action")
    if action not in handlers:
        raise ValueError("Which action? " + ", ".join(handlers))
    return handlers[action](settings, args)


# ---- pop-up cards -----------------------------------------------------------------------------------------------------

def result(text: str, title: str, headline: str, sub: str = "", rows=None, notes=None, buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card(RESULT, title, "", buttons=buttons, data={
        "headline": headline, "sub": sub, "rows": [[str(a), str(b)] for a, b in (rows or [])], "notes": list(notes or [])}))


def guide(text: str, title: str, sections, note: str = "", buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card(GUIDE, title, "", buttons=buttons, data={
        "sections": [{"heading": h, "lines": [str(x) for x in lines]} for h, lines in sections], "note": note}))


def check(text: str, title: str, headline: str, items, note: str = "", buttons=None) -> screen.Shown:
    """items: (label, status ok/warn/fail/todo, detail)."""
    return screen.Shown(text, screen.card(CHECK, title, "", buttons=buttons, data={
        "headline": headline, "note": note,
        "items": [{"label": str(a), "status": b if b in ("ok", "warn", "fail", "todo") else "todo", "detail": str(c)}
                  for a, b, c in items]}))


def board(text: str, title: str, columns, note: str = "", buttons=None) -> screen.Shown:
    """columns: (heading, [(label, small text, say line)])."""
    return screen.Shown(text, screen.card(BOARD, title, "", buttons=buttons, data={
        "columns": [{"title": h, "cards": [{"label": str(a), "small": str(b), "say": str(c)} for a, b, c in cards]}
                    for h, cards in columns], "note": note}))


def meter(text: str, title: str, rows, note: str = "", buttons=None) -> screen.Shown:
    """rows: (label, value text, share 0-100, small text)."""
    return screen.Shown(text, screen.card(METER, title, "", buttons=buttons, data={
        "rows": [{"label": str(a), "value": str(b), "pct": max(0, min(100, float(c))), "small": str(d)} for a, b, c, d in rows],
        "note": note}))


def table(text: str, title: str, columns, rows, card_id: str = "") -> screen.Shown:
    return screen.Shown(text, screen.card("table", title, card_id, columns=columns, rows=rows))


def chart(text: str, title: str, labels, values, kind: str = "bar", unit: str = "", card_id: str = "") -> screen.Shown:
    return screen.Shown(text, screen.card("chart", title, card_id, chart={"type": kind, "labels": labels, "values": values, "unit": unit}))


# ---- text measuring ---------------------------------------------------------------------------------------------------

def plain(text: str) -> str:
    """Markdown and HTML tags stripped so only the reading text is measured."""
    text = re.sub(r"```.*?```", " ", str(text or ""), flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s.*$", " ", text, flags=re.M)
    return re.sub(r"[*_`>]", "", text)


def words_of(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text)


def sentences_of(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text.strip())
    return [p for p in parts if words_of(p)]


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(n, 1)


def ease_band(score: float) -> str:
    for floor, name in ((90, "very easy"), (80, "easy"), (70, "fairly easy"), (60, "plain English"), (50, "fairly difficult"),
                        (30, "difficult")):
        if score >= floor:
            return name
    return "very difficult"


def reading_ease(text: str) -> dict:
    """Flesch reading ease and Flesch-Kincaid grade, worked out on this PC."""
    body = plain(text)
    words, sents = words_of(body), sentences_of(body)
    if len(words) < 5 or not sents:
        raise ValueError("Give me at least a sentence or two of text to measure.")
    syl = sum(syllables(w) for w in words)
    wps, spw = len(words) / len(sents), syl / len(words)
    ease = round(206.835 - 1.015 * wps - 84.6 * spw, 1)
    grade = round(0.39 * wps + 11.8 * spw - 15.59, 1)
    return {"words": len(words), "sentences": len(sents), "avg_sentence": round(wps, 1), "ease": ease, "grade": max(grade, 0.0),
            "band": ease_band(ease), "long": [s for s in sents if len(words_of(s)) > 25]}


def slugify(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", clean(title, 200).lower().replace("'", ""))
    stop = {"a", "an", "the", "of", "to", "and", "or", "in", "on", "for", "is", "are", "my"}
    keep = [w for w in words if w not in stop] or words
    return "-".join(keep[:6])
