"""Job applications: a tracker by stage (wishlist, applied, interview, offer, rejected), a kanban pop-up,
follow-up reminders, company research notes and a weekly job-search chart.

The board pops up as a "career-board" window (frontend/popup-career.js); its buttons send lines back to Alfred.
Kept in career-applications.json in the memory folder.
"""

from datetime import timedelta

import career_store as cs
import screen
from config import Settings

KIND = "career-board"
screen.EXTRA_KINDS.add(KIND)
STAGES = ["wishlist", "applied", "interview", "offer", "rejected"]
FOLLOW_UP_DAYS = 7
WEEKS = 8
ACTIONS = ["add", "move", "board", "list", "show", "follow_ups", "set_follow_up", "followed_up", "note", "notes",
           "remove", "stats"]


def _apps(settings: Settings) -> list[dict]:
    return [a for a in cs.load(settings, cs.APPLICATIONS, []) if isinstance(a, dict)]


def _label(a: dict) -> str:
    return f"{a['company']} - {a['role']}" if a.get("role") else a["company"]


def _pick(apps: list[dict], company, role=None) -> dict:
    name = cs.need(company, "company")
    hits = [a for a in apps if a["company"].lower() == name.lower()]
    hits = hits or [a for a in apps if name.lower() in _label(a).lower()]
    if role:
        hits = [a for a in hits if cs.clean(role).lower() in a.get("role", "").lower()] or hits
    if not hits:
        raise ValueError(f"I don't have an application for {name}.")
    if len(hits) > 1:
        raise ValueError(f"There are {len(hits)} applications for {name}; say which role.")
    return hits[0]


def _stage(value, default: str | None = None) -> str:
    text = cs.clean(value).lower() or default or ""
    if text not in STAGES:
        raise ValueError(f"The stages are {', '.join(STAGES)}.")
    return text


def _log(a: dict, stage: str) -> None:
    a.setdefault("history", []).append({"stage": stage, "date": cs.today().isoformat()})


def _follow(a: dict):
    return cs.parse_date(a.get("follow_up"), "follow-up date") if a.get("follow_up") else None


def _board(settings: Settings, apps: list[dict]) -> screen.Shown:
    cards = [{"label": _label(a), "company": a["company"], "role": a.get("role", ""), "stage": a["stage"],
              "follow_up": (cs.until(_follow(a)) if _follow(a) and a["stage"] not in ("rejected", "offer") else "")}
             for a in apps]
    counts = ", ".join(f"{sum(c['stage'] == s for c in cards)} {s}" for s in STAGES if any(c["stage"] == s for c in cards))
    return screen.Shown(f"Your job board: {counts or 'nothing yet'}.", screen.card(
        KIND, "Job applications", "career-board", data={"stages": STAGES, "cards": cards},
        buttons=[{"label": "Follow-ups due", "say": "Which job applications need a follow-up?"},
                 {"label": "Job stats", "say": "Show my job search stats."}]))


def _saved(settings: Settings, apps: list[dict], text: str) -> screen.Shown:
    cs.save(settings, cs.APPLICATIONS, apps)
    return screen.Shown(text, _board(settings, apps).card)


def add(settings: Settings, args: dict) -> screen.Shown:
    apps = _apps(settings)
    company = cs.need(args.get("company"), "company")
    role = cs.clean(args.get("role"), 80)
    if any(a["company"].lower() == company.lower() and a.get("role", "").lower() == role.lower() for a in apps):
        raise ValueError(f"You already have an application for {company}{' - ' + role if role else ''}.")
    if len(apps) >= cs.MAX_ROWS:
        raise ValueError("That's a lot of applications; remove some old ones first.")
    stage = _stage(args.get("stage"), "applied")
    follow = cs.parse_date(args.get("follow_up"), "follow-up date")
    if not follow and stage == "applied":
        follow = cs.today() + timedelta(days=FOLLOW_UP_DAYS)
    a = {"company": company, "role": role, "stage": stage, "url": cs.clean(args.get("url"), 300),
         "salary": cs.clean(args.get("salary"), 40), "follow_up": follow.isoformat() if follow else "",
         "notes": [], "history": []}
    _log(a, stage)
    if cs.clean(args.get("text")):
        a["notes"].append(cs.clean(args.get("text"), 1000))
    apps.append(a)
    return _saved(settings, apps, f"Added {_label(a)} as {stage}.")


def move(settings: Settings, args: dict) -> screen.Shown:
    apps = _apps(settings)
    a = _pick(apps, args.get("company"), args.get("role"))
    a["stage"] = _stage(args.get("stage"))
    _log(a, a["stage"])
    if a["stage"] == "applied" and not a.get("follow_up"):
        a["follow_up"] = (cs.today() + timedelta(days=FOLLOW_UP_DAYS)).isoformat()
    if a["stage"] in ("offer", "rejected"):
        a["follow_up"] = ""
    return _saved(settings, apps, f"Moved {_label(a)} to {a['stage']}.")


def board(settings: Settings) -> screen.Shown:
    return _board(settings, _apps(settings))


def listing(settings: Settings, args: dict) -> screen.Shown | str:
    apps = _apps(settings)
    if args.get("stage"):
        apps = [a for a in apps if a["stage"] == _stage(args.get("stage"))]
    if not apps:
        return "No job applications saved yet. Tell me about one and I'll track it."
    rows = [[_label(a), a["stage"], a.get("salary", ""), cs.short(_follow(a)) if _follow(a) else ""] for a in apps]
    return screen.Shown(f"{len(apps)} applications on the list.", screen.card(
        "table", "Applications", "career-applications", columns=["Job", "Stage", "Pay", "Follow up"], rows=rows,
        buttons=[{"label": "Board", "say": "Show my job board."}]))


def show(settings: Settings, args: dict) -> screen.Shown:
    a = _pick(_apps(settings), args.get("company"), args.get("role"))
    lines = [f"Stage: {a['stage']}"]
    for key, name in (("salary", "Pay"), ("url", "Link")):
        if a.get(key):
            lines.append(f"{name}: {a[key]}")
    if _follow(a):
        lines.append(f"Follow up: {cs.short(_follow(a))} ({cs.until(_follow(a))})")
    lines.append("History: " + ", ".join(f"{h['stage']} {h['date']}" for h in a.get("history", [])))
    if a.get("notes"):
        lines += ["", "Research notes:"] + [f"- {n}" for n in a["notes"]]
    return screen.Shown(f"{_label(a)} is at the {a['stage']} stage.", screen.card(
        "text", _label(a), f"career-app-{_label(a)}", text="\n".join(lines),
        buttons=[{"label": "Add a note", "say": f"Add a research note to my {a['company']} application: "},
                 {"label": "Interview questions", "say": "Show me common behavioural interview questions."}]))


def follow_ups(settings: Settings) -> screen.Shown | str:
    due = [a for a in _apps(settings) if _follow(a) and _follow(a) <= cs.today() and a["stage"] in ("applied", "interview", "wishlist")]
    if not due:
        return "No job follow-ups are due today."
    due.sort(key=_follow)
    items = [{"label": f"{_label(a)} - {cs.until(_follow(a))}", "say": f"I've followed up with {a['company']}"} for a in due]
    return screen.Shown(f"{len(due)} follow-ups due, first {_label(due[0])}.", screen.card(
        "list", "Follow-ups due", "career-followups", items=items))


def set_follow_up(settings: Settings, args: dict) -> screen.Shown:
    apps = _apps(settings)
    a = _pick(apps, args.get("company"), args.get("role"))
    day = cs.parse_date(args.get("follow_up"), "follow-up date")
    a["follow_up"] = day.isoformat() if day else ""
    text = f"I'll remind you to follow up with {a['company']} on {cs.short(day)}." if day else f"Cleared the follow-up for {a['company']}."
    return _saved(settings, apps, text)


def followed_up(settings: Settings, args: dict) -> screen.Shown:
    apps = _apps(settings)
    a = _pick(apps, args.get("company"), args.get("role"))
    day = cs.parse_date(args.get("follow_up"), "follow-up date") or cs.today() + timedelta(days=FOLLOW_UP_DAYS)
    a["follow_up"] = day.isoformat()
    a.setdefault("history", []).append({"stage": "followed up", "date": cs.today().isoformat()})
    return _saved(settings, apps, f"Noted. I'll nudge you about {a['company']} again on {cs.short(day)}.")


def note(settings: Settings, args: dict) -> screen.Shown:
    apps = _apps(settings)
    a = _pick(apps, args.get("company"), args.get("role"))
    text = cs.need(args.get("text"), "note", 1000)
    a.setdefault("notes", []).append(text)
    del a["notes"][:-50]
    cs.save(settings, cs.APPLICATIONS, apps)
    return notes(settings, args, f"Saved that research note for {a['company']}.")


def notes(settings: Settings, args: dict, said: str = "") -> screen.Shown | str:
    a = _pick(_apps(settings), args.get("company"), args.get("role"))
    if not a.get("notes"):
        return f"You have no research notes for {a['company']} yet."
    return screen.Shown(said or f"{len(a['notes'])} research notes for {a['company']}.", screen.card(
        "list", f"Research: {a['company']}", f"career-notes-{a['company']}", items=[{"label": n} for n in a["notes"]],
        buttons=[{"label": "Add a note", "say": f"Add a research note to my {a['company']} application: "}]))


def remove(settings: Settings, args: dict) -> screen.Shown | str:
    apps = _apps(settings)
    a = _pick(apps, args.get("company"), args.get("role"))
    if not args.get("confirmed"):
        return f"Shall I remove the {_label(a)} application? It can't be undone."
    apps.remove(a)
    return _saved(settings, apps, f"Removed {_label(a)}.")


def stats(settings: Settings) -> screen.Shown | str:
    apps = _apps(settings)
    if not apps:
        return "No applications yet, so no job-search stats."
    start = cs.week_start(cs.today()) - timedelta(weeks=WEEKS - 1)
    weeks = [start + timedelta(weeks=i) for i in range(WEEKS)]
    per = {w: 0 for w in weeks}
    for a in apps:
        for h in a.get("history", []):
            if h["stage"] == "applied":
                w = cs.week_start(cs.parse_date(h["date"]))
                if w in per:
                    per[w] += 1
    total = {s: sum(a["stage"] == s for a in apps) for s in STAGES}
    seen = sum(any(h["stage"] in ("interview", "offer") for h in a.get("history", [])) for a in apps)
    text = f"{len(apps)} applications, {seen} reached interview, {total['offer']} offers, {total['rejected']} rejections."
    return screen.Shown(text, screen.card(
        "chart", "Applications per week", "career-stats",
        chart={"type": "bar", "labels": [cs.short(w) for w in weeks], "values": list(per.values()), "unit": ""},
        buttons=[{"label": "Board", "say": "Show my job board."}]))


def tool_definitions() -> list[dict]:
    return [{
        "name": "career_applications",
        "description": "Job hunting tracker. Actions: add a job application (company, role, stage, follow_up date, "
                       "salary, url); move it to a stage (wishlist, applied, interview, offer, rejected); board "
                       "(kanban pop-up by stage); list (table, optional stage); show one; follow_ups (which are due "
                       "for a chase); set_follow_up; followed_up (I chased them); note (add a company research note "
                       "in text) and notes (show them); remove (set confirmed true only after the user says yes); "
                       "stats (weekly job-search chart).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "company": {"type": "string"},
                "role": {"type": "string", "description": "Job title, to tell two roles at one company apart."},
                "stage": {"type": "string", "enum": STAGES},
                "follow_up": {"type": "string", "description": "YYYY-MM-DD, 'tomorrow' or 'next week'; empty clears."},
                "salary": {"type": "string"},
                "url": {"type": "string"},
                "text": {"type": "string", "description": "A research note about the company or role."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"career_applications"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "add":
        return add(settings, args)
    if action == "move":
        return move(settings, args)
    if action == "list":
        return listing(settings, args)
    if action == "show":
        return show(settings, args)
    if action == "follow_ups":
        return follow_ups(settings)
    if action == "set_follow_up":
        return set_follow_up(settings, args)
    if action == "followed_up":
        return followed_up(settings, args)
    if action == "note":
        return note(settings, args)
    if action == "notes":
        return notes(settings, args)
    if action == "remove":
        return remove(settings, args)
    if action == "stats":
        return stats(settings)
    return board(settings)
