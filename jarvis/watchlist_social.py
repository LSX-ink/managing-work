"""Watching and reading with other people: who has borrowed your books and DVDs, the book club and film nights.

Stored in watchlist.json (lends, club, nights). Discussion questions for the book club are written by Alfred
himself and saved here; nothing is sent anywhere.
"""

from datetime import date

import homestore as hs
import screen
import watchlist_store as ws
from config import Settings

OVERDUE_DAYS = 30
MAX_NIGHTS = 100
ACTIONS = ["lend", "lend_return", "lend_list", "club_set", "club_show", "club_questions", "night_plan", "night_show"]


def lend(settings: Settings, args: dict) -> str:
    data = ws.load(settings)
    item, who = hs.need(args.get("item") or args.get("title"), "book or DVD", 120), hs.need(args.get("to"), "borrower", 60)
    day = hs.parse_day(args.get("date")).isoformat()
    ws.add_capped(data["lends"], {"item": item, "to": who, "date": day, "returned": ""}, "lending")
    ws.save(settings, data)
    return f"Noted: {item} is with {who} since {hs.spoken(date.fromisoformat(day))}."


def _out(data: dict) -> list[dict]:
    return [e for e in data["lends"] if isinstance(e, dict) and not e.get("returned")]


def lend_return(settings: Settings, args: dict) -> str:
    data = ws.load(settings)
    item = hs.clean(args.get("item") or args.get("title")).lower()
    who = hs.clean(args.get("to")).lower()
    found = [entry for entry in _out(data) if (not item or item in entry["item"].lower()) and (not who or who in entry["to"].lower())]
    if not (item or who):
        raise ValueError("Which item came back, or who returned something?")
    if not found:
        return "I've nothing lent out that matches that."
    if len(found) > 1:
        return "That matches several: " + "; ".join(f"{e['item']} with {e['to']}" for e in found) + ". Which one came back?"
    found[0]["returned"] = hs.today().isoformat()
    ws.save(settings, data)
    return f"Great, {found[0]['item']} is back from {found[0]['to']}."


def lend_list(settings: Settings) -> screen.Shown | str:
    out, today = _out(ws.load(settings)), hs.today()
    if not out:
        return "Nothing is lent out right now."
    rows, late = [], 0
    for e in sorted(out, key=lambda e: e["date"]):
        days = (today - date.fromisoformat(e["date"])).days
        late += days > OVERDUE_DAYS
        rows.append([e["item"], e["to"], hs.spoken(date.fromisoformat(e["date"])), f"{days} days" + (" (overdue)" if days > OVERDUE_DAYS else "")])
    text = f"{hs.plural(len(out), 'item')} lent out: " + "; ".join(f"{e['item']} with {e['to']}" for e in out[:5]) + "."
    if late:
        text += f" {late} out for over a month."
    return ws.board(text, "Lent out", "watchlist-lends", [ws.table(["Item", "With", "Since", "Out for"], rows)])


def club_set(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    club = data["club"]
    if args.get("title"):
        if hs.clean(args.get("title")) != club.get("book"):
            club["questions"] = []
        club["book"] = hs.clean(args.get("title"), 120)
    if args.get("date"):
        club["date"] = hs.parse_day(args.get("date")).isoformat()
    if args.get("place"):
        club["place"] = hs.clean(args.get("place"), 80)
    if not club.get("book"):
        raise ValueError("Which book is the club reading?")
    ws.save(settings, data)
    return club_show(settings, "Book club updated.")


def club_show(settings: Settings, said: str = "") -> screen.Shown | str:
    club = ws.load(settings)["club"]
    if not club.get("book"):
        return "No book club planned yet. Say 'our book club is reading Rebecca, meeting on Friday'."
    when = hs.spoken(date.fromisoformat(club["date"])) if club.get("date") else "date not set"
    facts = [["Next book", club["book"]], ["Meeting", when], ["Where", club.get("place") or "not set"]]
    sections = [ws.table([], facts)]
    if club.get("questions"):
        sections.append(ws.lines(club["questions"], "Discussion questions"))
    text = (said + " " if said else "") + f"Book club: {club['book']}, meeting {when}."
    return ws.board(text, "Book club", "watchlist-club", sections,
                    [{"label": "Discussion questions", "say": f"Write discussion questions for our book club book, {club['book']}."}])


def club_questions(settings: Settings, args: dict) -> screen.Shown | str:
    data = ws.load(settings)
    club = data["club"]
    if not club.get("book"):
        raise ValueError("Set the book club's book first.")
    questions = [hs.clean(q, 240) for q in (args.get("questions") or []) if hs.clean(q)][:12]
    if not questions:
        return (f"Write six thoughtful discussion questions for the book club book {club['book']} yourself, avoiding big "
                "spoilers in the first two, then call club_questions again with them in the questions argument to save them.")
    club["questions"] = questions
    ws.save(settings, data)
    return club_show(settings, f"Saved {len(questions)} discussion questions.")


def night_plan(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    night = {"title": hs.need(args.get("title"), "film", 120), "date": hs.parse_day(args.get("date")).isoformat(),
             "time": hs.clean(args.get("time"), 10), "who": ws.words(args.get("who"), 12), "snacks": ws.words(args.get("snacks"), 12)}
    data["nights"] = [n for n in data["nights"] if isinstance(n, dict) and not (n["title"] == night["title"] and n["date"] == night["date"])]
    data["nights"] = (data["nights"] + [night])[-MAX_NIGHTS:]
    ws.save(settings, data)
    return _night_board(night, f"Film night planned: {night['title']}")


def _night_board(night: dict, said: str) -> screen.Shown:
    when = hs.spoken(date.fromisoformat(night["date"])) + (f" at {night['time']}" if night["time"] else "")
    facts = [["Film", night["title"]], ["When", when], ["Who", ", ".join(night["who"]) or "not set"]]
    sections = [ws.table([], facts)]
    if night["snacks"]:
        sections.append(ws.lines([(s, f"Add {s} to my shopping list.") for s in night["snacks"]], "Snacks (tap to add to the shopping list)"))
    return ws.board(f"{said} on {when}.", "Film night", "watchlist-night", sections)


def night_show(settings: Settings) -> screen.Shown | str:
    today = hs.today().isoformat()
    ahead = sorted((n for n in ws.load(settings)["nights"] if isinstance(n, dict) and n["date"] >= today), key=lambda n: n["date"])
    if not ahead:
        return "No film night planned. Say 'plan a film night on Saturday with pizza and popcorn'."
    return _night_board(ahead[0], f"Next film night: {ahead[0]['title']}")


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "watch_social",
        "description": "Lending, book club and film nights. lend (item book or DVD, to = who borrowed it, date), "
                       "lend_return (item and/or to), lend_list shows what is lent out. club_set (title = next book, date, "
                       "place), club_show, club_questions (no questions: write them yourself, then call again with "
                       "questions to save). night_plan (title, date, time, who, snacks) and night_show for film night.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "item": text, "title": text, "to": text, "place": text, "time": text,
                "date": {"type": "string", "description": "YYYY-MM-DD, or today, tomorrow, a weekday."},
                "who": {"type": "array", "items": text}, "snacks": {"type": "array", "items": text},
                "questions": {"type": "array", "items": text},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"watch_social"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get("action")
    actions = {
        "lend": lambda: lend(settings, args),
        "lend_return": lambda: lend_return(settings, args),
        "lend_list": lambda: lend_list(settings),
        "club_set": lambda: club_set(settings, args),
        "club_show": lambda: club_show(settings),
        "club_questions": lambda: club_questions(settings, args),
        "night_plan": lambda: night_plan(settings, args),
        "night_show": lambda: night_show(settings),
    }
    if a not in actions:
        raise ValueError("Unknown watchlist action.")
    return actions[a]()
