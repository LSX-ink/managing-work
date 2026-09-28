"""Meeting notes (saved as Markdown in the Work folder), their action items, and a daily stand-up helper.

Action items pop up as a "work-actions" window (frontend/popup-work.js): a tick box per item and a To-do button
that says "add <item> to my to-do list" to Alfred.
"""

import memory
import screen
import worktools_store as ws
from config import Settings

KIND = "work-actions"
screen.EXTRA_KINDS.add(KIND)
MAX_MEETINGS = 300
MAX_STANDUPS = 120


def _markdown(m: dict) -> str:
    lines = [f"# {m['title']}", "", f"Date: {m['date']}", ""]
    if m.get("attendees"):
        lines += ["## Attendees", "", *[f"- {a}" for a in m["attendees"]], ""]
    if m.get("agenda"):
        lines += ["## Agenda", "", *[f"{i}. {a}" for i, a in enumerate(m["agenda"], 1)], ""]
    lines += ["## Notes", "", m.get("notes") or "(none yet)", ""]
    if m.get("actions"):
        lines += ["## Action items", "", *[f"- [{'x' if a.get('done') else ' '}] {a['text']}" for a in m["actions"]], ""]
    return "\n".join(lines)


def _write(settings: Settings, m: dict) -> None:
    folder = ws.work_folder(settings, "Meetings")
    path = memory.root(settings) / m["file"] if m.get("file") else None
    if not path or not path.parent.is_dir():
        path = memory.unique_path(folder / f"{m['date']} {memory.safe_name(m['title'][:45], 'meeting title')}.md")
        m["file"] = path.relative_to(memory.root(settings)).as_posix()
    path.write_text(_markdown(m), encoding="utf-8")


def _find(data: dict, title) -> dict:
    found = data["meetings"]
    if not found:
        raise ValueError("There are no meeting notes yet.")
    want = ws.clean(title).lower()
    if not want:
        return found[-1]
    match = [m for m in found if m["title"].lower() == want] or [m for m in found if want in m["title"].lower()]
    if not match:
        raise ValueError(f"I can't find a meeting called {ws.clean(title)}.")
    return match[-1]


def _shown(settings: Settings, m: dict, said: str) -> screen.Shown:
    path = memory.root(settings) / m["file"]
    return screen.Shown(said, screen.file_card(settings, path, buttons=[
        {"label": "Action items", "say": "Show my meeting action items."}]))


def meeting_add(settings: Settings, args: dict) -> screen.Shown:
    data = ws.meetings(settings)
    if len(data["meetings"]) >= MAX_MEETINGS:
        raise ValueError("That's a lot of meetings saved; the oldest notes stay in the Work folder, but I can't add more.")
    day = ws.parse_date(args.get("date")) or ws.today()
    m = {"title": ws.need(args.get("title"), "meeting title", 80), "date": day.isoformat(),
         "attendees": ws.words(args.get("attendees"), 30, 60), "agenda": ws.words(args.get("agenda"), 30, 200),
         "notes": ws.clean(args.get("notes"), 5000),
         "actions": [{"text": a, "done": False} for a in ws.words(args.get("actions"), 30, 150)]}
    _write(settings, m)
    data["meetings"].append(m)
    ws.save(settings, ws.MEETINGS, data)
    return _shown(settings, m, f"Saved the {m['title']} meeting notes with {len(m['actions'])} action items.")


def meeting_update(settings: Settings, args: dict) -> screen.Shown:
    data = ws.meetings(settings)
    m = _find(data, args.get("title"))
    extra = ws.clean(args.get("notes"), 5000)
    if extra:
        m["notes"] = f"{m.get('notes', '')}\n\n{extra}".strip()[-20000:]
    have = {a["text"].lower() for a in m["actions"]}
    new = [a for a in ws.words(args.get("actions"), 30, 150) if a.lower() not in have]
    m["actions"] += [{"text": a, "done": False} for a in new]
    m["attendees"] = ws.words(m["attendees"] + list(args.get("attendees") or []), 30, 60)
    m["agenda"] = ws.words(m["agenda"] + list(args.get("agenda") or []), 30, 200)
    _write(settings, m)
    ws.save(settings, ws.MEETINGS, data)
    return _shown(settings, m, f"Updated the {m['title']} notes" + (f" and added {len(new)} action items." if new else "."))


def meeting_show(settings: Settings, title) -> screen.Shown:
    m = _find(ws.meetings(settings), title)
    return _shown(settings, m, f"Showing the {m['title']} notes from {m['date']}.")


def meetings_list(settings: Settings) -> screen.Shown:
    found = list(reversed(ws.meetings(settings)["meetings"]))
    items = [{"label": f"{m['date']}: {m['title']}", "say": f"Show the meeting notes for {m['title']}."} for m in found]
    said = f"{len(found)} meetings saved; the latest is {found[0]['title']}." if found else "No meeting notes yet."
    return screen.Shown(said, screen.card("list", "Meetings", "work-meetings", items=items))


def actions_show(settings: Settings, said: str = "") -> screen.Shown:
    data = ws.meetings(settings)
    items = [{"text": a["text"], "meeting": m["title"], "done": bool(a.get("done"))}
             for m in reversed(data["meetings"]) for a in m["actions"]]
    items.sort(key=lambda i: i["done"])
    left = sum(not i["done"] for i in items)
    said = said or (f"{left} open action items." if items else "No action items from meetings yet.")
    return screen.Shown(said, screen.card(KIND, "Action items", "work-actions", data={"items": items[:150]}))


def action_tick(settings: Settings, text, done: bool) -> screen.Shown:
    data = ws.meetings(settings)
    want = ws.need(text, "action item", 150).lower()
    pool = [a for m in data["meetings"] for a in m["actions"] if bool(a.get("done")) != done]
    match = [a for a in pool if a["text"].lower() == want] or [a for a in pool if want in a["text"].lower()]
    if not match:
        raise ValueError(f"There's no {'open' if done else 'ticked'} action item like {ws.clean(text)}.")
    match[0]["done"] = done
    for m in data["meetings"]:
        if match[0] in m["actions"]:
            _write(settings, m)
    ws.save(settings, ws.MEETINGS, data)
    return actions_show(settings, f"{'Ticked off' if done else 'Reopened'} {match[0]['text']}.")


def standup_save(settings: Settings, args: dict) -> str:
    data = ws.meetings(settings)
    day = ws.parse_date(args.get("date")) or ws.today()
    entry = {k: ws.clean(args.get(k), 1000) for k in ("yesterday", "today", "blockers")}
    if not any(entry.values()):
        raise ValueError("Tell me what you did yesterday, what you're doing today, and any blockers.")
    old = data["standups"].get(day.isoformat()) or {}
    data["standups"][day.isoformat()] = {k: entry[k] or old.get(k, "") for k in entry}
    for k in sorted(data["standups"])[:-MAX_STANDUPS]:
        del data["standups"][k]
    ws.save(settings, ws.MEETINGS, data)
    return f"Saved your stand-up for {ws.short(day)}."


def standup_last(settings: Settings) -> screen.Shown | str:
    ups = ws.meetings(settings)["standups"]
    days = [d for d in sorted(ups) if d <= ws.today().isoformat()]
    if not days:
        return "No stand-ups saved yet."
    s = ups[days[-1]]
    text = "\n".join(f"{label}: {s.get(k) or 'nothing noted'}"
                     for label, k in (("Yesterday", "yesterday"), ("Today", "today"), ("Blockers", "blockers")))
    said = f"Your stand-up from {ws.short(ws.parse_date(days[-1]))}. " + text.replace("\n", ". ") + "."
    return screen.Shown(said, screen.card("text", f"Stand-up {days[-1]}", "work-standup", text=text))


def tool_definitions() -> list[dict]:
    listed = {"type": "array", "items": {"type": "string"}}
    return [{
        "name": "work_meetings",
        "description": "Work meeting notes, action items and stand-ups. actions: meeting_add (title, attendees' "
                       "names, agenda, notes, action items; saved as Markdown in the Work folder), meeting_update "
                       "(add notes or action items to a meeting), meeting_show, meetings (list), action_items (open "
                       "action items with tick boxes), action_done / action_undone (tick or untick one), "
                       "standup_save (yesterday, today, blockers), standup_last (read back the last stand-up).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["meeting_add", "meeting_update", "meeting_show", "meetings",
                                                      "action_items", "action_done", "action_undone", "standup_save",
                                                      "standup_last"]},
                "title": {"type": "string", "description": "Meeting title; empty means the latest meeting."},
                "date": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'yesterday'; default today."},
                "attendees": {**listed, "description": "First names only."},
                "agenda": listed,
                "notes": {"type": "string"},
                "actions": {**listed, "description": "Action items, e.g. ['Sam to send the budget']."},
                "item": {"type": "string", "description": "action_done / action_undone: the action item."},
                "yesterday": {"type": "string"},
                "today": {"type": "string"},
                "blockers": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"work_meetings"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "meeting_add":
        return meeting_add(settings, args)
    if action == "meeting_update":
        return meeting_update(settings, args)
    if action == "meeting_show":
        return meeting_show(settings, args.get("title"))
    if action == "action_items":
        return actions_show(settings)
    if action in ("action_done", "action_undone"):
        return action_tick(settings, args.get("item"), action == "action_done")
    if action == "standup_save":
        return standup_save(settings, args)
    if action == "standup_last":
        return standup_last(settings)
    return meetings_list(settings)
