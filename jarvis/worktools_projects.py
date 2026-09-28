"""Work projects: add, list and archive them, park ideas, see deadlines, a project summary and a weekly report.

Summaries pop up as "work-summary" windows (frontend/popup-work.js): a row of numbers, then short sections.
"""

from datetime import timedelta

import screen
import worktools_store as ws
from config import Settings

KIND = "work-summary"
screen.EXTRA_KINDS.add(KIND)
STATUSES = ["planning", "active", "on hold", "done"]
MAX_PROJECTS = 100
MAX_IDEAS = 100


def summary_card(title: str, card_id: str, stats: list, sections: list, buttons=None) -> dict:
    return screen.card(KIND, title, card_id, buttons=buttons, data={
        "stats": [{"label": str(a), "value": str(b)} for a, b in stats],
        "sections": [{"heading": h, "items": [str(i) for i in items][:40]} for h, items in sections]})


def _status(value, default: str = "active") -> str:
    text = ws.clean(value).lower()
    if not text:
        return default
    if text not in STATUSES:
        raise ValueError(f"The status can be {', '.join(STATUSES)}.")
    return text


def add(settings: Settings, name, status, due, notes) -> screen.Shown:
    found = ws.projects(settings)
    name = ws.need(name, "project name", 60)
    if any(k.lower() == name.lower() for k in found):
        raise ValueError(f"There's already a project called {name}.")
    if len(found) >= MAX_PROJECTS:
        raise ValueError("That's a lot of projects; archive or finish some first.")
    day = ws.parse_date(due, "due date")
    found[name] = {"status": _status(status), "due": day.isoformat() if day else "", "notes": ws.clean(notes, 1000),
                   "ideas": [], "archived": False, "created": ws.today().isoformat()}
    ws.save(settings, ws.PROJECTS, found)
    return listing(settings, False, f"Added the {name} project" + (f", due {ws.short(day)}." if day else "."))


def update(settings: Settings, name, status, due, notes) -> screen.Shown:
    key = ws.project(settings, name)
    found = ws.projects(settings)
    p = found[key]
    if ws.clean(status):
        p["status"] = _status(status)
    if due is not None and ws.clean(due):
        p["due"] = ws.parse_date(due, "due date").isoformat()
    if ws.clean(notes):
        p["notes"] = f"{p.get('notes', '')}\n{ws.clean(notes, 1000)}".strip()[-2000:]
    ws.save(settings, ws.PROJECTS, found)
    return listing(settings, False, f"Updated {key}: {p['status']}" + (f", due {p['due']}." if p.get("due") else "."))


def archive(settings: Settings, name, restore: bool) -> screen.Shown:
    key = ws.project(settings, name, archived=True)
    found = ws.projects(settings)
    found[key]["archived"] = not restore
    ws.save(settings, ws.PROJECTS, found)
    return listing(settings, False,
                   f"{'Brought back' if restore else 'Archived'} the {key} project.")


def listing(settings: Settings, archived: bool, said: str = "") -> screen.Shown:
    found = ws.projects(settings)
    boards = ws.boards(settings)
    week = ws.week_start(ws.today())
    mins = ws.minutes_by_project(ws.time_data(settings)["entries"], week, week + timedelta(days=6))
    rows = []
    for name, p in sorted(found.items(), key=lambda kv: (kv[1].get("due") or "9999", kv[0].lower())):
        if bool(p.get("archived")) != archived:
            continue
        b = boards.get(name) or {}
        last = (b.get("columns") or ws.DEFAULT_COLUMNS)[-1]
        open_cards = sum(1 for c in b.get("cards", []) if c.get("column") != last)
        rows.append([name, p.get("status", ""), p.get("due") or "-", str(open_cards), ws.hm(mins.get(name, 0))])
    what = "archived projects" if archived else "work projects"
    if not said:
        said = f"{len(rows)} {what}: {', '.join(r[0] for r in rows)}." if rows else f"No {what}."
    other = [{"label": "Show live" if archived else "Show archived",
              "say": "List my work projects." if archived else "List my archived work projects."}]
    return screen.Shown(said, screen.card("table", "Archived projects" if archived else "Work projects",
                                          "work-projects", columns=["Project", "Status", "Due", "Open cards", "This week"],
                                          rows=rows, buttons=other))


def idea_add(settings: Settings, name, text) -> screen.Shown:
    key = ws.project(settings, name)
    found = ws.projects(settings)
    ideas = found[key].setdefault("ideas", [])
    idea = ws.need(text, "idea", 200)
    if len(ideas) >= MAX_IDEAS:
        raise ValueError("That parking lot is full; clear some ideas first.")
    if idea.lower() not in (i.lower() for i in ideas):
        ideas.append(idea)
    ws.save(settings, ws.PROJECTS, found)
    return ideas_show(settings, key, f"Parked that idea for {key}. {len(ideas)} ideas there.")


def ideas_show(settings: Settings, name, said: str = "") -> screen.Shown:
    key = ws.project(settings, name)
    ideas = ws.projects(settings)[key].get("ideas", [])
    items = [{"label": i, "say": f"Add card {i} to the {key} board."} for i in ideas]
    said = said or (f"{len(ideas)} ideas parked for {key}." if ideas else f"No ideas parked for {key} yet.")
    return screen.Shown(said, screen.card("list", f"{key} ideas", f"work-ideas-{key}", items=items))


def idea_remove(settings: Settings, name, text, confirmed: bool):
    key = ws.project(settings, name)
    found = ws.projects(settings)
    ideas = found[key].get("ideas", [])
    k = ws.find(ideas, ws.need(text, "idea"))
    if k is None:
        raise ValueError(f"There's no idea like {ws.clean(text)} parked for {key}.")
    if not confirmed:
        return f"Ask the user to confirm removing the idea '{k}' from {key}, then call again with confirmed true."
    ideas.remove(k)
    ws.save(settings, ws.PROJECTS, found)
    return ideas_show(settings, key, f"Removed that idea from {key}.")


def upcoming(settings: Settings, days: int = 14, only: str = "") -> list[tuple]:
    """(date, what, project) due within days (overdue included), soonest first."""
    today = ws.today()
    end = today + timedelta(days=days)
    out = []
    boards = ws.boards(settings)
    for name, p in ws.projects(settings).items():
        if p.get("archived") or (only and name != only):
            continue
        if p.get("due") and p.get("status") != "done":
            out.append((p["due"], "Project deadline", name))
        b = boards.get(name) or {}
        last = (b.get("columns") or ws.DEFAULT_COLUMNS)[-1]
        out += [(c["due"], c["title"], name) for c in b.get("cards", []) if c.get("due") and c.get("column") != last]
    return sorted(x for x in out if x[0] <= end.isoformat())


def deadlines(settings: Settings) -> screen.Shown:
    today = ws.today()
    found = upcoming(settings)
    rows = [[what, name, ws.short(ws.parse_date(d)), ws.until(ws.parse_date(d), today)] for d, what, name in found]
    if found:
        d, what, name = found[0]
        said = f"{len(found)} deadlines in the next 14 days; the first is {what} for {name}, {ws.until(ws.parse_date(d), today)}."
    else:
        said = "Nothing due in the next 14 days."
    return screen.Shown(said, screen.card("table", "Work deadlines", "work-deadlines",
                                          columns=["What", "Project", "Due", "When"], rows=rows))


def summary(settings: Settings, name) -> screen.Shown:
    key = ws.project(settings, name)
    p = ws.projects(settings)[key]
    b = ws.board(ws.boards(settings), key)
    today = ws.today()
    entries = ws.time_data(settings)["entries"]
    week = ws.week_start(today)
    total = sum(float(e.get("minutes") or 0) for e in entries if e.get("project") == key)
    this_week = ws.minutes_by_project(entries, week, week + timedelta(days=6)).get(key, 0)
    stats = [(col, sum(c["column"] == col for c in b["cards"])) for col in b["columns"]]
    stats += [("This week", ws.hm(this_week)), ("All time", ws.hm(total))]
    dues = [f"{what}: {ws.short(ws.parse_date(d))} ({ws.until(ws.parse_date(d), today)})"
            for d, what, _ in upcoming(settings, 14, key)]
    notes = [line for line in (p.get("notes") or "").splitlines() if line]
    notes += [f"{c['title']}: {c['notes']}" for c in b["cards"] if c.get("notes")]
    sections = [("Status", [p.get("status", "active") + (f", due {p['due']}" if p.get("due") else "")]),
                ("Deadlines", dues or ["Nothing due in the next 14 days."]),
                ("Notes", notes or ["No notes yet."]),
                ("Ideas parked", p.get("ideas") or ["None."])]
    counts = ", ".join(f"{n} {c}" for c, n in stats[:len(b["columns"])])
    said = f"{key}: {counts}; {ws.hm(this_week)} this week, {len(dues)} deadlines coming up."
    return screen.Shown(said, summary_card(f"{key} summary", f"work-summary-{key}", stats, sections,
                                           [{"label": "Board", "say": f"Show the {key} board."},
                                            {"label": "Ideas", "say": f"Show the ideas for {key}."}]))


def weekly_report(settings: Settings, week_value) -> screen.Shown:
    start = ws.week_of(week_value)
    end = start + timedelta(days=6)
    mins = ws.minutes_by_project(ws.time_data(settings)["entries"], start, end)
    finished = []
    for name, b in ws.boards(settings).items():
        finished += [f"{c['title']} ({name})" for c in b.get("cards", [])
                     if c.get("done_on") and start.isoformat() <= c["done_on"] <= end.isoformat()]
    data = ws.meetings(settings)
    held = [f"{m['date']}: {m['title']}" for m in data["meetings"] if start.isoformat() <= m["date"] <= end.isoformat()]
    open_actions = [f"{a['text']} ({m['title']})" for m in data["meetings"] for a in m.get("actions", []) if not a.get("done")]
    total = sum(mins.values())
    stats = [("Hours", ws.hm(total)), ("Cards done", len(finished)), ("Meetings", len(held)),
             ("Open actions", len(open_actions))]
    sections = [("Hours per project", [f"{k}: {ws.hm(v)}" for k, v in sorted(mins.items(), key=lambda kv: -kv[1])]
                 or ["No time logged."]),
                ("Cards finished", finished or ["None."]),
                ("Meetings held", held or ["None."]),
                ("Open action items", open_actions or ["None."])]
    said = (f"Week of {ws.short(start)}: {ws.hm(total)} worked, {len(finished)} cards finished, "
            f"{len(held)} meetings, {len(open_actions)} open action items.")
    return screen.Shown(said, summary_card(f"Work week of {ws.short(start)}", "work-report", stats, sections,
                                           [{"label": "Timesheet", "say": "Show my work timesheet for this week."}]))


def tool_definitions() -> list[dict]:
    return [{
        "name": "work_projects",
        "description": "Work projects. actions: add a project (status, due date, notes), list projects "
                       "(archived true for archived ones), update status/due/notes, archive or restore a project, "
                       "idea_add / ideas / idea_remove for a project's ideas parking lot, deadlines (projects and "
                       "cards due in the next 14 days with countdowns), summary of one project (board counts, time "
                       "spent, deadlines, notes), weekly_report (hours per project, cards finished, meetings, open "
                       "action items). Set confirmed true only after the user confirms an idea_remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "list", "update", "archive", "restore", "idea_add",
                                                      "ideas", "idea_remove", "deadlines", "summary", "weekly_report"]},
                "project": {"type": "string"},
                "status": {"type": "string", "enum": STATUSES},
                "due": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'tomorrow'."},
                "notes": {"type": "string"},
                "idea": {"type": "string"},
                "archived": {"type": "boolean"},
                "week": {"type": "string", "description": "weekly_report: 'this', 'last' or a YYYY-MM-DD in that week."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"work_projects"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action, project = args.get("action"), args.get("project")
    if action == "add":
        return add(settings, project, args.get("status"), args.get("due"), args.get("notes"))
    if action == "update":
        return update(settings, project, args.get("status"), args.get("due"), args.get("notes"))
    if action in ("archive", "restore"):
        return archive(settings, project, action == "restore")
    if action == "idea_add":
        return idea_add(settings, project, args.get("idea"))
    if action == "ideas":
        return ideas_show(settings, project)
    if action == "idea_remove":
        return idea_remove(settings, project, args.get("idea"), bool(args.get("confirmed")))
    if action == "deadlines":
        return deadlines(settings)
    if action == "summary":
        return summary(settings, project)
    if action == "weekly_report":
        return weekly_report(settings, args.get("week"))
    return listing(settings, bool(args.get("archived")))
