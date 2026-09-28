"""Little helpers for everyday life: a quick-capture inbox, where things are kept, three good things a day,
pros and cons for a decision, reusable checklists, and who has borrowed what.

The inbox is Inbox.md in the Ideas folder; the rest are small JSON files in the memory folder.
"""

import re
from datetime import date

import homestore as hs
import memory
import screen
from config import Settings

WHERE, GRATITUDE = "where.json", "routines-gratitude.json"
DECISIONS, CHECKLISTS, LOANS = "routines-decisions.json", "routines-checklists.json", "routines-loans.json"
MAX_ROWS = 200
MAX_ITEMS = 40
CAPTURE_ACTIONS = ["inbox_add", "inbox_read", "inbox_clear", "where_save", "where_find", "where_list",
                   "where_forget", "gratitude_add", "gratitude_month"]
LIST_ACTIONS = ["decision_add", "decision_show", "decision_list", "decision_delete", "checklist_save",
                "checklist_start", "checklist_list", "checklist_delete", "loan_add", "loan_returned", "loan_list"]


def _load(settings: Settings, name: str) -> dict:
    return hs.load(settings, name, {})


def _put(settings: Settings, name: str, rows: dict, key: str, value) -> None:
    if key not in rows and len(rows) >= MAX_ROWS:
        raise ValueError("That list is full; remove something first.")
    rows[key] = value
    hs.save(settings, name, rows)


def _key(rows: dict, name, what: str) -> str:
    key = hs.find(rows, hs.need(name, what))
    if key is None:
        raise ValueError(f"I haven't got a {what} called {hs.clean(name)}." + (f" There's: {', '.join(rows)}." if rows else ""))
    return key


def _same(rows: dict, name: str) -> str:
    return next((k for k in rows if k.lower() == name.lower()), name)


# ---- Quick-capture inbox -------------------------------------------------------------------------

def inbox_path(settings: Settings):
    return memory.folder(settings, 0) / "Inbox.md"


def _inbox_lines(settings: Settings) -> list[str]:
    try:
        text = inbox_path(settings).read_text(encoding="utf-8")
    except OSError:
        return []
    return [line[2:] for line in text.splitlines() if line.startswith("- ")]


def inbox_add(settings: Settings, text) -> str:
    text = hs.need(text, "note", 500)
    path = inbox_path(settings)
    lines = _inbox_lines(settings)
    if len(lines) >= 500:
        raise ValueError("The inbox is full; clear it first.")
    lines.append(f"{hs.now():%Y-%m-%d %H:%M} {text}")
    path.write_text("# Inbox\n\n" + "".join(f"- {line}\n" for line in lines), encoding="utf-8")
    return f"Noted in your inbox. {hs.plural(len(lines), 'note')} in it."


def inbox_read(settings: Settings) -> str | screen.Shown:
    lines = _inbox_lines(settings)
    if not lines:
        return "The inbox is empty."
    card = screen.card("list", "Inbox", "routines-inbox", items=[{"label": line} for line in lines],
                       buttons=[{"label": "Clear inbox", "say": "Clear my inbox."}])
    return screen.Shown(f"{hs.plural(len(lines), 'note')} in the inbox (on screen):\n" + "\n".join(lines), card)


def inbox_clear(settings: Settings, confirmed: bool) -> str:
    lines = _inbox_lines(settings)
    if not lines:
        return "The inbox is already empty."
    if not confirmed:
        return f"Ask the user to confirm clearing {hs.plural(len(lines), 'note')} from the inbox, then call again with confirmed true."
    inbox_path(settings).write_text("# Inbox\n\n", encoding="utf-8")
    return "The inbox is cleared."


# ---- Where things are ------------------------------------------------------------------------------

def where_save(settings: Settings, thing, place) -> str:
    rows = _load(settings, WHERE)
    thing = re.sub(r"(?i)^(my|the) ", "", hs.need(thing, "thing", 60))
    place = hs.need(place, "place", 120)
    key = _same(rows, thing)
    _put(settings, WHERE, rows, key, {"place": place, "since": hs.today().isoformat()})
    return f"Remembered: {key} is {place}."


def where_find(settings: Settings, thing) -> str:
    rows = _load(settings, WHERE)
    words = [w for w in re.findall(r"\w+", hs.clean(thing).lower()) if w not in {"my", "the", "a"}]
    found = [k for k in rows if words and all(w in k.lower() for w in words)]
    if not found:
        return f"I don't know where {hs.clean(thing)} is." + (f" I know about: {', '.join(rows)}." if rows else "")
    return " ".join(f"{k} is {rows[k]['place']} (noted {rows[k]['since']})." for k in found)


def where_list(settings: Settings) -> str | screen.Shown:
    rows = _load(settings, WHERE)
    if not rows:
        return "I haven't been told where anything is yet."
    table = [[k, v["place"], v["since"]] for k, v in sorted(rows.items(), key=lambda kv: kv[0].lower())]
    card = screen.card("table", "Where things are", "routines-where", columns=["Thing", "Where", "Noted"], rows=table)
    return screen.Shown(f"{hs.plural(len(rows), 'thing')} remembered; they're on the screen.", card)


def where_forget(settings: Settings, thing) -> str:
    rows = _load(settings, WHERE)
    key = _key(rows, thing, "thing")
    del rows[key]
    hs.save(settings, WHERE, rows)
    return f"Forgotten where {key} is."


# ---- Three good things ---------------------------------------------------------------------------------

def gratitude_add(settings: Settings, things) -> str:
    things = [hs.clean(t, 200) for t in (things or []) if hs.clean(t)]
    if not things:
        raise ValueError("What are you grateful for?")
    rows = _load(settings, GRATITUDE)
    day = hs.today().isoformat()
    rows[day] = (rows.get(day) or []) + things[:10]
    cutoff = date(hs.today().year - 3, 1, 1).isoformat()
    hs.save(settings, GRATITUDE, {d: v for d, v in rows.items() if d >= cutoff})
    return f"Logged {hs.plural(len(things), 'good thing')} for today; {len(rows[day])} so far today."


def gratitude_month(settings: Settings, month=None) -> str | screen.Shown:
    month = hs.clean(month)[:7] or hs.today().strftime("%Y-%m")
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("Give the month as YYYY-MM.")
    days = {d: v for d, v in sorted(_load(settings, GRATITUDE).items()) if d.startswith(month)}
    if not days:
        return f"No good things logged for {month} yet."
    count = sum(len(v) for v in days.values())
    title = f"Good things: {date.fromisoformat(month + '-01'):%B %Y}"
    card = screen.card("table", title, "routines-gratitude", text=f"{count} good things on {len(days)} days.",
                       columns=["Day", "Good things"], rows=[[d[8:], "; ".join(v)] for d, v in days.items()])
    return screen.Shown(f"{count} good things on {len(days)} days in {month}; they're on the screen.", card)


# ---- Decisions: weighted pros and cons ------------------------------------------------------------------

def decision_add(settings: Settings, decision, points) -> str | screen.Shown:
    rows = _load(settings, DECISIONS)
    key = _same(rows, hs.need(decision, "decision", 80))
    have = list(rows.get(key) or [])
    for p in points or []:
        text = hs.clean((p or {}).get("text"), 120)
        if text and p.get("side") in ("pro", "con"):
            have.append({"side": p["side"], "text": text, "weight": int(hs.number(p.get("weight") or 1, "weight", 1, 5))})
    if not have:
        raise ValueError("Give at least one pro or con.")
    _put(settings, DECISIONS, rows, key, have[:MAX_ITEMS])
    return decision_show(settings, key)


def decision_show(settings: Settings, decision) -> screen.Shown:
    rows = _load(settings, DECISIONS)
    key = _key(rows, decision, "decision")
    points = rows[key]
    pros = sum(p["weight"] for p in points if p["side"] == "pro")
    cons = sum(p["weight"] for p in points if p["side"] == "con")
    lean = "leaning yes" if pros > cons else "leaning no" if cons > pros else "evenly balanced"
    table = [["Pro" if p["side"] == "pro" else "Con", p["text"], str(p["weight"])]
             for p in sorted(points, key=lambda p: (p["side"] != "pro", -p["weight"]))]
    table += [["", "Pros total", str(pros)], ["", "Cons total", str(cons)], ["", "Score", f"{pros - cons:+d}"]]
    card = screen.card("table", f"Decision: {key}", f"decision-{key}", text=f"Pros {pros}, cons {cons}: {lean}.",
                       columns=["Side", "Point", "Weight"], rows=table)
    return screen.Shown(f"{key}: pros score {pros}, cons {cons}, so {lean}. The table is on the screen.", card)


def decision_list(settings: Settings) -> str | screen.Shown:
    rows = _load(settings, DECISIONS)
    if not rows:
        return "No decisions being weighed up."
    card = screen.card("list", "Decisions", "routines-decisions",
                       items=[{"label": k, "say": f"Show my pros and cons for {k}."} for k in rows])
    return screen.Shown(f"Decisions: {', '.join(rows)}. They're on the screen.", card)


def _delete(settings: Settings, name: str, label, what: str, confirmed: bool) -> str:
    rows = _load(settings, name)
    key = _key(rows, label, what)
    if not confirmed:
        return f"Ask the user to confirm deleting the {key} {what}, then call again with confirmed true."
    del rows[key]
    hs.save(settings, name, rows)
    return f"Deleted the {key} {what}."


# ---- Checklist templates -----------------------------------------------------------------------------------

def checklist_save(settings: Settings, name, items) -> str:
    rows = _load(settings, CHECKLISTS)
    key = _same(rows, hs.need(name, "checklist", 60))
    items = [hs.clean(i, 120) for i in (items or []) if hs.clean(i)][:MAX_ITEMS]
    if not items:
        raise ValueError("What goes on the checklist?")
    _put(settings, CHECKLISTS, rows, key, items)
    return f"Saved the {key} checklist with {hs.plural(len(items), 'item')}."


def checklist_start(settings: Settings, name) -> screen.Shown:
    rows = _load(settings, CHECKLISTS)
    key = _key(rows, name, "checklist")
    card = screen.card("list", f"Checklist: {key}", f"checklist-{key}", checks=True,
                       items=[{"label": i} for i in rows[key]])
    return screen.Shown(f"The {key} checklist is on the screen with {hs.plural(len(rows[key]), 'item')} to tick.", card)


def checklist_list(settings: Settings) -> str | screen.Shown:
    rows = _load(settings, CHECKLISTS)
    if not rows:
        return "No checklists saved yet."
    card = screen.card("list", "Checklists", "routines-checklists",
                       items=[{"label": f"{k} ({len(v)} items)", "say": f"Start my {k} checklist."} for k, v in rows.items()])
    return screen.Shown(f"Checklists: {', '.join(rows)}. Click one on the screen to start it.", card)


# ---- Lent and borrowed ---------------------------------------------------------------------------------------

def _loans(settings: Settings) -> list[dict]:
    return [r for r in hs.load(settings, LOANS, []) if isinstance(r, dict) and {"thing", "person", "direction"} <= r.keys()]


def loan_add(settings: Settings, thing, person, direction, since=None) -> str:
    if direction not in ("lent", "borrowed"):
        raise ValueError("Say whether it was lent or borrowed.")
    loans = _loans(settings)
    if len(loans) >= MAX_ROWS:
        loans = [r for r in loans if not r.get("returned")] or loans[-MAX_ROWS + 1:]
    row = {"thing": hs.need(thing, "thing", 80), "person": hs.need(person, "person", 60), "direction": direction,
           "since": hs.parse_day(since).isoformat() if since else hs.today().isoformat(), "returned": ""}
    hs.save(settings, LOANS, loans + [row])
    return (f"Noted: {row['person']} has your {row['thing']}." if direction == "lent"
            else f"Noted: you've borrowed {row['thing']} from {row['person']}.")


def loan_returned(settings: Settings, thing) -> str:
    words = re.findall(r"\w+", hs.clean(thing).lower())
    loans = _loans(settings)
    hit = [r for r in loans if not r.get("returned") and words and all(w in f"{r['thing']} {r['person']}".lower() for w in words)]
    if not hit:
        return "Nothing out on loan matches that."
    for r in hit:
        r["returned"] = hs.today().isoformat()
    hs.save(settings, LOANS, loans)
    return "Marked returned: " + "; ".join(f"{r['thing']} ({r['person']})" for r in hit) + "."


def loan_list(settings: Settings) -> str | screen.Shown:
    out = [r for r in _loans(settings) if not r.get("returned")]
    if not out:
        return "Nothing is lent out or borrowed."
    today = hs.today()
    table = [[r["thing"], r["person"], r["direction"], r["since"], str((today - date.fromisoformat(r["since"])).days)]
             for r in sorted(out, key=lambda r: r["since"])]
    card = screen.card("table", "Lent and borrowed", "routines-loans",
                       columns=["Thing", "Who", "Lent or borrowed", "Since", "Days"], rows=table)
    lent = [f"{r['thing']} with {r['person']}" for r in out if r["direction"] == "lent"]
    borrowed = [f"{r['thing']} from {r['person']}" for r in out if r["direction"] == "borrowed"]
    said = "; ".join(filter(None, [f"Lent out: {', '.join(lent)}" if lent else "",
                                   f"Borrowed: {', '.join(borrowed)}" if borrowed else ""]))
    return screen.Shown(said + ". The list is on the screen.", card)


# ---- Tools ------------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [
        {
            "name": "capture_and_remember",
            "description": "Quick notes and remembering things. Inbox: 'note that ...' inbox_add (text), inbox_read "
                           "('read my inbox'), inbox_clear (set confirmed true only after the user confirms). Where "
                           "things are: 'my passport is in the top drawer' where_save (thing, place), 'where's my "
                           "passport?' where_find, where_list, where_forget. Gratitude or three good things: "
                           "gratitude_add (things), gratitude_month (month YYYY-MM, default this month).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": CAPTURE_ACTIONS},
                    "text": {"type": "string"},
                    "thing": {"type": "string", "description": "e.g. 'passport'."},
                    "place": {"type": "string", "description": "e.g. 'in the top drawer'."},
                    "things": {"type": "array", "items": {"type": "string"}},
                    "month": {"type": "string"},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "decisions_checklists_loans",
            "description": "Decision helper with weighted pros and cons: decision_add (decision, points with side "
                           "pro/con and weight 1-5), decision_show (score table), decision_list, decision_delete. "
                           "Reusable checklists like 'leaving the house': checklist_save (name, items), "
                           "checklist_start (tick boxes on screen), checklist_list, checklist_delete. Lend and "
                           "borrow tracker: loan_add (thing, person, direction lent/borrowed, since YYYY-MM-DD), "
                           "loan_returned (thing), loan_list. Deletes need confirmed true, set only after the user "
                           "confirms.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": LIST_ACTIONS},
                    "decision": {"type": "string", "description": "e.g. 'move to Leeds'."},
                    "points": {"type": "array", "items": {"type": "object", "properties": {
                        "side": {"type": "string", "enum": ["pro", "con"]}, "text": {"type": "string"},
                        "weight": {"type": "integer", "description": "1 to 5, default 1."}},
                        "required": ["side", "text"], "additionalProperties": False}},
                    "name": {"type": "string", "description": "Checklist name."},
                    "items": {"type": "array", "items": {"type": "string"}},
                    "thing": {"type": "string"},
                    "person": {"type": "string"},
                    "direction": {"type": "string", "enum": ["lent", "borrowed"]},
                    "since": {"type": "string"},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {"capture_and_remember", "decisions_checklists_loans"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get("action")
    confirmed = bool(args.get("confirmed"))
    actions = {
        "inbox_add": lambda: inbox_add(settings, args.get("text")),
        "inbox_read": lambda: inbox_read(settings),
        "inbox_clear": lambda: inbox_clear(settings, confirmed),
        "where_save": lambda: where_save(settings, args.get("thing"), args.get("place")),
        "where_find": lambda: where_find(settings, args.get("thing")),
        "where_list": lambda: where_list(settings),
        "where_forget": lambda: where_forget(settings, args.get("thing")),
        "gratitude_add": lambda: gratitude_add(settings, args.get("things") or [args.get("text")]),
        "gratitude_month": lambda: gratitude_month(settings, args.get("month")),
        "decision_add": lambda: decision_add(settings, args.get("decision"), args.get("points")),
        "decision_show": lambda: decision_show(settings, args.get("decision")),
        "decision_list": lambda: decision_list(settings),
        "decision_delete": lambda: _delete(settings, DECISIONS, args.get("decision"), "decision", confirmed),
        "checklist_save": lambda: checklist_save(settings, args.get("name"), args.get("items")),
        "checklist_start": lambda: checklist_start(settings, args.get("name")),
        "checklist_list": lambda: checklist_list(settings),
        "checklist_delete": lambda: _delete(settings, CHECKLISTS, args.get("name"), "checklist", confirmed),
        "loan_add": lambda: loan_add(settings, args.get("thing"), args.get("person"), args.get("direction"),
                                     args.get("since")),
        "loan_returned": lambda: loan_returned(settings, args.get("thing")),
        "loan_list": lambda: loan_list(settings),
    }
    if a not in actions or (name == "capture_and_remember") != (a in CAPTURE_ACTIONS):
        raise ValueError(f"Unknown action {a}.")
    return actions[a]()
