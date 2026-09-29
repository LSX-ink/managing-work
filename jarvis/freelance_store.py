"""Shared bits for the freelance abilities: freelance-*.json files in the memory folder, money, dates, pop-up cards.

Files: freelance-clients.json, freelance-leads.json, freelance-projects.json, freelance-time.json (entries and the running
timer), freelance-scope.json, freelance-retainers.json, freelance-testimonials.json, freelance-checklists.json and
freelance-profile.json (your rate numbers). Proposals, case studies and drafts are saved as files in the "Freelance"
folder. Everything stays on this PC; nothing is ever sent, posted or paid anywhere.
"""

import re
from datetime import date, timedelta
from pathlib import Path

import memory
import screen
from config import Settings
from creatorbiz_store import clean, find, gbp, load, long_date, need, parse_date, save, short, today, until  # noqa: F401 (re-exported)

CLIENTS = "freelance-clients.json"
LEADS = "freelance-leads.json"
PROJECTS = "freelance-projects.json"
TIME = "freelance-time.json"
SCOPE = "freelance-scope.json"
RETAINERS = "freelance-retainers.json"
TESTIMONIALS = "freelance-testimonials.json"
CHECKLISTS = "freelance-checklists.json"
PROFILE = "freelance-profile.json"
FOLDER = "Freelance"
MAX_ROWS = 2000
HONEST = "This is a planning estimate from the numbers you gave, not a promise of income."
TAX_NOTE = "Tax and legal rules differ for everyone, so check GOV.UK for the current rules."

BOARD = "freelance-board"
CALC = "freelance-calc"
SHEET = "freelance-timesheet"
METER = "freelance-meter"
CHECK = "freelance-checklist"
screen.EXTRA_KINDS.update({BOARD, CALC, SHEET, METER, CHECK})


def number(value, what: str, allow_zero: bool = False, top: float = 10_000_000) -> float:
    try:
        n = float(str(value if value is not None else "").replace("£", "").replace(",", "").replace("%", "").strip())
    except ValueError:
        raise ValueError(f"Give the {what} as a number.") from None
    if n < 0 or (n == 0 and not allow_zero) or n > top:
        raise ValueError(f"That {what} doesn't look right.")
    return round(n, 2)


def num(n: float) -> str:
    return f"{n:g}" if abs(n * 10 - round(n * 10)) < 1e-9 else f"{n:.2f}"


def hm(hours: float) -> str:
    minutes = round(hours * 60)
    return f"{minutes // 60}h {minutes % 60:02d}m" if minutes >= 60 else f"{minutes}m"


def write_file(settings: Settings, name: str, text: str) -> Path:
    """Save a text file in the Freelance folder without overwriting an older one."""
    folder = memory.root(settings) / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = memory.unique_path(folder / memory.safe_name(name, "file name"))
    path.write_text(text, encoding="utf-8")
    return path


def file_shown(settings: Settings, path: Path, text: str) -> screen.Shown:
    return screen.Shown(text, screen.file_card(settings, path))


def draft(settings: Settings, title: str, body: str, said: str, save_as: str | None = None) -> screen.Shown:
    """A draft that pops up as text and is also saved as a Markdown file. Never sent anywhere."""
    if save_as:
        path = write_file(settings, save_as + ".md", body)
        said += f" It is saved as {path.name} in the Freelance folder."
    return screen.Shown(said + " Nothing has been sent.", screen.card("text", title, "", text=body))


def calc(text: str, title: str, headline: str, sub: str = "", rows=None, notes=None, buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card(CALC, title, "", buttons=buttons, data={
        "headline": headline, "sub": sub, "rows": [[str(a), str(b)] for a, b in (rows or [])], "notes": list(notes or [])}))


def meter(text: str, title: str, rows: list[dict], note: str = "", buttons=None) -> screen.Shown:
    """rows: {label, used, max, text, say?}; the bar fills used/max."""
    return screen.Shown(text, screen.card(METER, title, "", buttons=buttons, data={"rows": rows, "note": note}))


def table(text: str, title: str, columns, rows, buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card("table", title, "", columns=columns, rows=rows, buttons=buttons))


def dispatch(handlers: dict, action, settings: Settings, args: dict, what: str):
    if action not in handlers:
        raise ValueError(f"Which {what} action? " + ", ".join(handlers))
    return handlers[action](settings, args)


def next_id(rows: list[dict]) -> int:
    return max([r.get("id", 0) for r in rows] + [0]) + 1


def rows_of(settings: Settings, name: str) -> list[dict]:
    return [r for r in load(settings, name, []) if isinstance(r, dict)]


def clients(settings: Settings) -> list[dict]:
    return rows_of(settings, CLIENTS)


def client_name(settings: Settings, name) -> str:
    """The saved client's name if it matches, else the name as typed."""
    typed = need(name, "client", 60)
    key = find([c["name"] for c in clients(settings)], typed)
    return key or typed


def known_client(settings: Settings, name) -> dict:
    typed = need(name, "client", 60)
    key = find([c["name"] for c in clients(settings)], typed)
    hit = next((c for c in clients(settings) if c["name"] == key), None)
    if hit is None:
        raise ValueError(f"I don't have a client called {typed}.")
    return hit


def projects(settings: Settings) -> list[dict]:
    return rows_of(settings, PROJECTS)


def pick_project(settings: Settings, args: dict, key: str = "project") -> dict:
    rows = projects(settings)
    if args.get("project_id") is not None:
        hit = next((p for p in rows if p["id"] == int(args["project_id"])), None)
    else:
        name = need(args.get(key), "project", 80).lower()
        hits = [p for p in rows if p["name"].lower() == name] or [p for p in rows if name in p["name"].lower()]
        if args.get("client"):
            hits = [p for p in hits if args["client"].lower() in p["client"].lower()] or hits
        live = [p for p in hits if p["status"] != "done"] or hits
        if len(live) > 1:
            raise ValueError(f"{len(live)} projects match {name}; give the project number.")
        hit = live[0] if live else None
    if not hit:
        raise ValueError("I can't find that project.")
    return hit


def time_data(settings: Settings) -> dict:
    data = load(settings, TIME, {})
    data.setdefault("entries", [])
    return data


def add_time(settings: Settings, client: str, project: str, hours: float, day: date | None = None, note: str = "",
             billable: bool = True) -> dict:
    data = time_data(settings)
    if len(data["entries"]) >= MAX_ROWS * 5:
        raise ValueError("The time log is full; tidy it first.")
    entry = {"date": (day or today()).isoformat(), "client": client, "project": project, "hours": round(hours, 2),
             "note": note, "billable": billable, "billed": False}
    data["entries"].append(entry)
    save(settings, TIME, data)
    return entry


def entries(settings: Settings, start: date | None = None, end: date | None = None, client: str | None = None) -> list[dict]:
    out = []
    for e in time_data(settings)["entries"]:
        day = date.fromisoformat(e["date"])
        if (start and day < start) or (end and day > end):
            continue
        if client and client.lower() not in e["client"].lower():
            continue
        out.append(e)
    return out


def week_start(text=None, ref: date | None = None) -> date:
    ref = ref or today()
    t = clean(text).lower()
    if t in ("last", "last week"):
        ref -= timedelta(days=7)
    elif t and t not in ("this", "this week"):
        ref = parse_date(t, "week")
    return ref - timedelta(days=ref.weekday())


def month_bounds(text=None) -> tuple[date, date]:
    t = clean(text)
    try:
        first = date.fromisoformat(t + "-01") if t else today().replace(day=1)
    except ValueError:
        raise ValueError("Give the month as YYYY-MM.") from None
    return first, (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def profile(settings: Settings) -> dict:
    return load(settings, PROFILE, {})


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9 _-]", "", clean(text, 50)).strip() or "Freelance"
