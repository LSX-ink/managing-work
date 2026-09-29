"""Shot lists per shoot and photo projects (like a 365 project).

Shot lists (photo-shots.json) pop up with a tick box per shot (kind "photo-shots"); clicking a shot tells Alfred to
tick it, so the list on disk is always the truth. Projects (photo-projects.json) are a target number of photos,
either one a day (a 365) or a count (100 portraits), shown as a grid of squares that fill up (kind "photo-progress").
Deleting a list or project needs confirmed true.
"""

from datetime import timedelta

import homestore as hs
import photo_data
import photo_store as ps
import screen
from config import Settings

LISTS, PROJECTS = "photo-shots.json", "photo-projects.json"
MAX_LISTS, MAX_SHOTS, MAX_PROJECTS, MAX_CELLS = 40, 80, 20, 400
ACTIONS = ("shots_new", "shots_add", "shots_show", "shots_tick", "shots_remove", "shots_reset", "shots_lists",
           "shots_delete", "shots_starter", "project_start", "project_log", "project_progress", "project_list",
           "project_delete")

for _kind in ("photo-shots", "photo-progress"):
    screen.EXTRA_KINDS.add(_kind)


def _load(settings: Settings, name: str) -> dict:
    return {k: v for k, v in hs.load(settings, name, {}).items() if isinstance(v, dict)}


def _key(found: dict, label, what: str) -> str:
    text = hs.clean(label)
    if not text and len(found) == 1:
        return next(iter(found))
    k = hs.find(found, hs.need(text, what))
    if k is None:
        raise ValueError(f"I haven't got a {what} called {text}.")
    return k


def _type(value) -> str:
    text = hs.clean(value).lower()
    if text and text not in photo_data.SHOOTS:
        raise ValueError(f"I have starter lists for: {', '.join(photo_data.SHOOTS)}.")
    return text


# Shot lists

def _shots_card(name: str, entry: dict) -> dict:
    shots = [{"n": i + 1, "text": s["text"], "done": s["done"],
              "say": f"{'Untick' if s['done'] else 'Tick off'} shot {i + 1} on my {name} shot list."}
             for i, s in enumerate(entry["shots"])]
    return screen.card("photo-shots", f"Shot list: {name}", f"photo-shots-{name}",
                       buttons=[{"label": "Clear ticks", "say": f"Clear the ticks on my {name} shot list."}],
                       data={"name": name, "type": entry.get("type", ""), "shots": shots})


def _show(name: str, entry: dict) -> screen.Shown:
    done = sum(1 for s in entry["shots"] if s["done"])
    return screen.Shown(f"{name}: {done} of {len(entry['shots'])} shots done.", _shots_card(name, entry))


def shots_new(settings: Settings, name, kind, shots) -> screen.Shown:
    found = _load(settings, LISTS)
    label = hs.need(name, "shoot name", 50)
    if hs.find(found, label) and hs.find(found, label).lower() == label.lower():
        raise ValueError(f"You already have a shot list called {label}; use add a shot instead.")
    if len(found) >= MAX_LISTS:
        raise ValueError("That's as many shot lists as I can keep; delete one first.")
    kind = _type(kind)
    texts = [hs.clean(s, 120) for s in shots or [] if hs.clean(s)] or (photo_data.SHOOTS[kind]["shots"] if kind else [])
    if not texts:
        raise ValueError("Give me some shots for the list, or a shoot type to start from.")
    found[label] = {"type": kind, "shots": [{"text": s, "done": False} for s in texts[:MAX_SHOTS]]}
    hs.save(settings, LISTS, found)
    return _show(label, found[label])


def shots_add(settings: Settings, name, shots) -> screen.Shown:
    found = _load(settings, LISTS)
    k = _key(found, name, "shot list")
    have = {s["text"].lower() for s in found[k]["shots"]}
    new = [hs.clean(s, 120) for s in shots or [] if hs.clean(s) and hs.clean(s).lower() not in have]
    if not new:
        raise ValueError("Which shots should I add?")
    if len(found[k]["shots"]) + len(new) > MAX_SHOTS:
        raise ValueError("That shot list is full.")
    found[k]["shots"] += [{"text": s, "done": False} for s in new]
    hs.save(settings, LISTS, found)
    return _show(k, found[k])


def _index(entry: dict, shot) -> int:
    text = hs.clean(shot).lower()
    if text.isdigit() and 1 <= int(text) <= len(entry["shots"]):
        return int(text) - 1
    hits = [i for i, s in enumerate(entry["shots"]) if text and text in s["text"].lower()]
    if len(hits) != 1:
        raise ValueError("Which shot? Give its number or a few words from it.")
    return hits[0]


def shots_show(settings: Settings, name) -> screen.Shown:
    found = _load(settings, LISTS)
    k = _key(found, name, "shot list")
    return _show(k, found[k])


def shots_tick(settings: Settings, name, shot, done) -> screen.Shown:
    found = _load(settings, LISTS)
    k = _key(found, name, "shot list")
    i = _index(found[k], shot)
    found[k]["shots"][i]["done"] = done is not False
    hs.save(settings, LISTS, found)
    return _show(k, found[k])


def shots_remove(settings: Settings, name, shot) -> screen.Shown:
    found = _load(settings, LISTS)
    k = _key(found, name, "shot list")
    found[k]["shots"].pop(_index(found[k], shot))
    hs.save(settings, LISTS, found)
    return _show(k, found[k])


def shots_reset(settings: Settings, name) -> screen.Shown:
    found = _load(settings, LISTS)
    k = _key(found, name, "shot list")
    for s in found[k]["shots"]:
        s["done"] = False
    hs.save(settings, LISTS, found)
    return _show(k, found[k])


def shots_lists(settings: Settings) -> screen.Shown:
    found = _load(settings, LISTS)
    if not found:
        return screen.Shown("You haven't got any shot lists yet. Say 'make a wedding shot list' to start one.",
                            ps.table("Shot lists", ["List", "Done"], [], "photo-shot-lists"))
    rows = [[k, f"{sum(1 for s in v['shots'] if s['done'])} of {len(v['shots'])}", v.get("type", "")]
            for k, v in found.items()]
    return screen.Shown(f"You have {hs.plural(len(found), 'shot list')}.",
                        ps.table("Shot lists", ["List", "Done", "Type"], rows, "photo-shot-lists"))


def shots_delete(settings: Settings, name, confirmed) -> str:
    found = _load(settings, LISTS)
    k = _key(found, name, "shot list")
    if confirmed is not True:
        return f"Deleting the {k} shot list can't be undone. Ask the user to confirm, then call again with confirmed true."
    del found[k]
    hs.save(settings, LISTS, found)
    return f"Deleted the {k} shot list."


def shots_starter(kind) -> screen.Shown:
    kind = _type(kind)
    if not kind:
        rows = [[k, str(len(v["shots"]))] for k, v in photo_data.SHOOTS.items()]
        return screen.Shown("Here are the starter shot lists I know.",
                            ps.table("Starter shot lists", ["Shoot type", "Shots"], rows, "photo-starters"))
    entry = {"type": kind, "shots": [{"text": s, "done": False} for s in photo_data.SHOOTS[kind]["shots"]]}
    card = _shots_card(f"{kind} starter", entry)
    card["buttons"] = [{"label": "Save this list", "say": f"Make a {kind} shot list called {kind} shoot."}]
    for s in card["data"]["shots"]:
        s["say"] = ""
    return screen.Shown(f"A {kind} starter list with {len(entry['shots'])} shots.", card)


# Projects

def _cells(p: dict) -> tuple[list[bool], int]:
    """A filled or empty square per day (or per photo for a count project) and how many are filled."""
    entries = p["entries"]
    target = min(p["target"], MAX_CELLS)
    if p["kind"] == "count":
        cells = [i < len(entries) for i in range(target)]
    else:
        start = hs.parse_day(p["start"])
        dates = {e["date"] for e in entries}
        cells = [(start + timedelta(days=i)).isoformat() in dates for i in range(target)]
    return cells, len(entries)


def _streak(p: dict) -> int:
    dates = {e["date"] for e in p["entries"]}
    day = hs.today()
    if day.isoformat() not in dates:
        day -= timedelta(days=1)
    run = 0
    while day.isoformat() in dates:
        run += 1
        day -= timedelta(days=1)
    return run


def _progress(name: str, p: dict) -> screen.Shown:
    cells, done = _cells(p)
    facts = [["Photos", f"{done} of {p['target']}"]]
    spoken = f"{name}: {done} of {p['target']} photos."
    if p["kind"] == "daily":
        start = hs.parse_day(p["start"])
        elapsed = max(0, min(p["target"], (hs.today() - start).days + 1))
        missed = max(0, elapsed - done)
        facts += [["Day", f"{elapsed} of {p['target']}"], ["Missed", str(missed)], ["Streak", f"{_streak(p)} days"],
                  ["Finishes", (start + timedelta(days=p["target"] - 1)).isoformat()]]
        spoken += f" Day {elapsed}, {hs.plural(missed, 'day')} missed, streak {_streak(p)}."
    else:
        facts.append(["Still to go", str(max(0, p["target"] - done))])
    card = screen.card("photo-progress", f"Project: {name}", f"photo-project-{name}",
                       buttons=[{"label": "Log today's photo", "say": f"Log today's photo for {name}."}],
                       data={"name": name, "kind": p["kind"], "target": p["target"], "cells": cells,
                             "done": done, "facts": facts,
                             "notes": [f"{e['date']}: {e['note']}" for e in p["entries"][-3:] if e.get("note")]})
    return screen.Shown(spoken, card)


def project_start(settings: Settings, name, target, kind, start) -> screen.Shown:
    found = _load(settings, PROJECTS)
    label = hs.need(name, "project name", 50)
    if hs.find(found, label) and hs.find(found, label).lower() == label.lower():
        raise ValueError(f"You already have a project called {label}.")
    if len(found) >= MAX_PROJECTS:
        raise ValueError("That's as many projects as I can keep.")
    kind = hs.clean(kind).lower() or "daily"
    if kind not in ("daily", "count"):
        raise ValueError("A project is either daily (one photo a day) or count.")
    found[label] = {"kind": kind, "target": int(hs.number(target or 365, "target", 1, 5000)),
                    "start": hs.parse_day(start).isoformat(), "entries": []}
    hs.save(settings, PROJECTS, found)
    return _progress(label, found[label])


def project_log(settings: Settings, name, note, day) -> screen.Shown:
    found = _load(settings, PROJECTS)
    k = _key(found, name, "project")
    p = found[k]
    when = hs.parse_day(day).isoformat()
    entry = {"date": when, "note": hs.clean(note, 120)}
    if p["kind"] == "daily":
        p["entries"] = [e for e in p["entries"] if e["date"] != when] + [entry]
        p["entries"].sort(key=lambda e: e["date"])
    else:
        p["entries"].append(entry)
    hs.save(settings, PROJECTS, found)
    return _progress(k, p)


def project_progress(settings: Settings, name) -> screen.Shown:
    found = _load(settings, PROJECTS)
    k = _key(found, name, "project")
    return _progress(k, found[k])


def project_list(settings: Settings) -> screen.Shown:
    found = _load(settings, PROJECTS)
    rows = [[k, v["kind"], f"{len(v['entries'])} of {v['target']}"] for k, v in found.items()]
    return screen.Shown(f"You have {hs.plural(len(found), 'photo project')}." if found else "No photo projects yet.",
                        ps.table("Photo projects", ["Project", "Type", "Photos"], rows, "photo-projects"))


def project_delete(settings: Settings, name, confirmed) -> str:
    found = _load(settings, PROJECTS)
    k = _key(found, name, "project")
    if confirmed is not True:
        return f"Deleting the {k} project can't be undone. Ask the user to confirm, then call again with confirmed true."
    del found[k]
    hs.save(settings, PROJECTS, found)
    return f"Deleted the {k} project."


def tool_definitions() -> list[dict]:
    return [{
        "name": "photo_shoots",
        "description": "Photography shot lists and photo projects. Shot lists per shoot: shots_new (name, optional type "
                       "for a starter list, or shots), shots_add, shots_show (pop-up with tick boxes), shots_tick (shot "
                       "number or words, done false to untick), shots_remove, shots_reset, shots_lists, shots_starter "
                       "(preview ideas by type), shots_delete. Projects like a 365: project_start (name, target, "
                       "project_kind daily or count), project_log (today's photo, optional note or date), "
                       "project_progress (grid pop-up), project_list, project_delete. Set confirmed true on deletes only "
                       "after the user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "name": {"type": "string", "description": "Shot list or project name."},
                "type": {"type": "string", "enum": list(photo_data.SHOOTS)},
                "shots": {"type": "array", "items": {"type": "string"}},
                "shot": {"type": ["string", "integer"], "description": "Shot number or a few words from it."},
                "done": {"type": "boolean"},
                "target": {"type": "integer"}, "project_kind": {"type": "string", "enum": ["daily", "count"]},
                "start": {"type": "string", "description": "YYYY-MM-DD or today."},
                "note": {"type": "string"}, "date": {"type": "string", "description": "YYYY-MM-DD, today or yesterday."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"photo_shoots"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    table = {
        "shots_new": lambda: shots_new(settings, a("name"), a("type"), a("shots")),
        "shots_add": lambda: shots_add(settings, a("name"), a("shots")),
        "shots_show": lambda: shots_show(settings, a("name")),
        "shots_tick": lambda: shots_tick(settings, a("name"), a("shot"), a("done")),
        "shots_remove": lambda: shots_remove(settings, a("name"), a("shot")),
        "shots_reset": lambda: shots_reset(settings, a("name")),
        "shots_lists": lambda: shots_lists(settings),
        "shots_delete": lambda: shots_delete(settings, a("name"), a("confirmed")),
        "shots_starter": lambda: shots_starter(a("type")),
        "project_start": lambda: project_start(settings, a("name"), a("target"), a("project_kind"), a("start")),
        "project_log": lambda: project_log(settings, a("name"), a("note"), a("date")),
        "project_progress": lambda: project_progress(settings, a("name")),
        "project_list": lambda: project_list(settings),
        "project_delete": lambda: project_delete(settings, a("name"), a("confirmed")),
    }
    if a("action") not in table:
        raise ValueError(f"I can't do {a('action')}. Try: {', '.join(ACTIONS)}.")
    return table[a("action")]()
