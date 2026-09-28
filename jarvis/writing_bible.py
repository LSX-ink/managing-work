"""A project's story bible: characters, world and setting notes (places and lore), and a plot planner of scenes
in three acts. Everything is kept with the project in writing.json.
"""

import homestore as hs
import screen
import writing_store as ws
from config import Settings

ACTIONS = ["character_add", "character_list", "character_card", "character_delete", "world_add", "world_list",
           "world_delete", "scene_add", "scene_move", "scene_list", "scene_delete"]
CHARACTER_FIELDS = ["role", "traits", "appearance", "notes"]
WORLD_TYPES = ["place", "lore"]


def confirm_first(what: str, args: dict) -> str | None:
    if args.get("confirmed") is not True:
        return f"Ask the user to confirm deleting {what}, then call again with confirmed true."
    return None


def entry_key(found: dict, name, what: str) -> str:
    key = hs.find(found, hs.need(name, what))
    if key is None:
        raise ValueError(f"There's no {what} called {hs.clean(name)}.")
    return key


# ---- Characters ------------------------------------------------------------------------------------

def character_add(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    name = hs.need(args.get("name"), "character name", 60)
    found = next((k for k in p["characters"] if k.lower() == name.lower()), None)
    if found is None and len(p["characters"]) >= ws.MAX_ENTRIES:
        raise ValueError("That's as many characters as I can keep.")
    c = p["characters"].setdefault(found or name, {f: "" for f in CHARACTER_FIELDS})
    for field in CHARACTER_FIELDS:
        if hs.clean(args.get(field), 1000):
            c[field] = hs.clean(args[field], 1000)
    ws.save(settings, data)
    return character_card(settings, {"project": key, "name": found or name},
                          f"{'Updated' if found else 'Added'} {found or name} in {key}'s character bible.")


def character_list(settings: Settings, args: dict) -> screen.Shown | str:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    if not p["characters"]:
        return f"{key} has no characters yet."
    names = sorted(p["characters"], key=str.lower)
    rows = [[n, p["characters"][n].get("role", ""), p["characters"][n].get("traits", "")] for n in names]
    items = [{"label": n, "say": f"Show the character card for {n} in {key}."} for n in names]
    return screen.Shown(f"{key} has {ws.s(len(names), 'character')}: {', '.join(names)}.",
                        ws.studio(f"{key}: characters", f"writing-chars-{ws.slug(key)}", [
                            {"type": "table", "columns": ["Name", "Role", "Traits"], "rows": rows},
                            {"type": "list", "title": "Open a card", "items": items}]))


def character_card(settings: Settings, args: dict, said: str = "") -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    name = entry_key(p["characters"], args.get("name"), "character")
    c = p["characters"][name]
    fields = [{"label": f.title(), "value": c.get(f) or "-"} for f in ("role", "traits", "appearance")]
    sections = [{"type": "fields", "items": fields}]
    if c.get("notes"):
        sections.append({"type": "text", "title": "Notes", "text": c["notes"]})
    facts = "; ".join(f"{f}: {c[f]}" for f in CHARACTER_FIELDS if c.get(f))
    return screen.Shown(said or f"{name}. {facts or 'No details yet.'}",
                        ws.studio(name, f"writing-char-{ws.slug(key)}-{ws.slug(name)}", sections,
                                  [{"label": "All characters", "say": f"List the characters in {key}."}]))


def character_delete(settings: Settings, args: dict) -> screen.Shown | str:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    name = entry_key(p["characters"], args.get("name"), "character")
    ask = confirm_first(f"the character {name} from {key}", args)
    if ask:
        return ask
    del p["characters"][name]
    ws.save(settings, data)
    return character_list(settings, {"project": key}) if p["characters"] else f"Deleted {name}; {key} has no characters now."


# ---- World and setting -----------------------------------------------------------------------------

def world_add(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    name = hs.need(args.get("name"), "place or lore entry", 60)
    found = next((k for k in p["world"] if k.lower() == name.lower()), None)
    if found is None and len(p["world"]) >= ws.MAX_ENTRIES:
        raise ValueError("That's as many world notes as I can keep.")
    entry = p["world"].setdefault(found or name, {"type": "place", "notes": ""})
    if args.get("type") in WORLD_TYPES:
        entry["type"] = args["type"]
    if hs.clean(args.get("notes"), 2000):
        entry["notes"] = hs.clean(args["notes"], 2000)
    ws.save(settings, data)
    return world_list(settings, {"project": key}, f"{'Updated' if found else 'Added'} the {entry['type']} {found or name}.")


def world_list(settings: Settings, args: dict, said: str = "") -> screen.Shown | str:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    if not p["world"]:
        return f"{key} has no world notes yet."
    sections = []
    for kind, title in (("place", "Places"), ("lore", "Lore")):
        items = [{"label": n, "note": e.get("notes", "")} for n, e in sorted(p["world"].items(), key=lambda kv: kv[0].lower())
                 if e.get("type", "place") == kind]
        if items:
            sections.append({"type": "list", "title": f"{title} ({len(items)})", "items": items})
    if not said:
        said = f"{key}'s world: " + "; ".join(f"{n}: {e.get('notes', '')[:120]}" for n, e in list(p["world"].items())[:12])
    return screen.Shown(said, ws.studio(f"{key}: world", f"writing-world-{ws.slug(key)}", sections))


def world_delete(settings: Settings, args: dict) -> screen.Shown | str:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    name = entry_key(p["world"], args.get("name"), "world note")
    ask = confirm_first(f"the world note {name}", args)
    if ask:
        return ask
    del p["world"][name]
    ws.save(settings, data)
    return world_list(settings, {"project": key}, f"Deleted {name}.") if p["world"] else f"Deleted {name}."


# ---- Plot planner ------------------------------------------------------------------------------------

def act_of(value, default: int = 1) -> int:
    return int(hs.number(value if value not in (None, "") else default, "act", 1, 3))


def scene_index(p: dict, name) -> int:
    text = hs.need(name, "scene")
    key = hs.find([x["title"] for x in p["scenes"]], text)
    if key is None:
        raise ValueError(f"There's no scene called {text}.")
    return next(i for i, x in enumerate(p["scenes"]) if x["title"] == key)


def place_scene(p: dict, scene: dict, position) -> None:
    """Put a scene into its act, at a 1-based position within that act (default: its end)."""
    same = [i for i, x in enumerate(p["scenes"]) if x["act"] == scene["act"]]
    if position in (None, "") or not same:
        after = [i for i, x in enumerate(p["scenes"]) if x["act"] <= scene["act"]]
        at = (max(after) + 1) if after else 0
    else:
        n = int(hs.number(position, "position", 1, ws.MAX_ENTRIES)) - 1
        at = same[n] if n < len(same) else same[-1] + 1
    p["scenes"].insert(at, scene)


def scene_add(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    if len(p["scenes"]) >= ws.MAX_ENTRIES:
        raise ValueError("That's as many scenes as I can keep.")
    title = hs.need(args.get("name"), "scene", 80)
    if any(x["title"].lower() == title.lower() for x in p["scenes"]):
        raise ValueError(f"There's already a scene called {title}.")
    scene = {"title": title, "act": act_of(args.get("act")), "summary": hs.clean(args.get("notes"), 1000)}
    place_scene(p, scene, args.get("position"))
    ws.save(settings, data)
    return scene_list(settings, {"project": key}, f"Added the scene {title} to act {scene['act']}.")


def scene_move(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    scene = p["scenes"].pop(scene_index(p, args.get("name")))
    scene["act"] = act_of(args.get("act"), scene["act"])
    place_scene(p, scene, args.get("position"))
    ws.save(settings, data)
    at = [x for x in p["scenes"] if x["act"] == scene["act"]].index(scene) + 1
    return scene_list(settings, {"project": key}, f"Moved {scene['title']} to act {scene['act']}, scene {at}.")


def scene_list(settings: Settings, args: dict, said: str = "") -> screen.Shown | str:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    if not p["scenes"]:
        return f"{key} has no scenes planned yet."
    sections = []
    for act in (1, 2, 3):
        rows = [[str(i), x["title"], x.get("summary", "")]
                for i, x in enumerate((x for x in p["scenes"] if x["act"] == act), 1)]
        if rows:
            sections.append({"type": "table", "title": f"Act {act}", "columns": ["#", "Scene", "What happens"],
                             "rows": rows})
    counts = ", ".join(f"act {a}: {sum(1 for x in p['scenes'] if x['act'] == a)}" for a in (1, 2, 3))
    return screen.Shown(said or f"{key}'s plot has {ws.s(len(p['scenes']), 'scene')} ({counts}).",
                        ws.studio(f"{key}: plot", f"writing-plot-{ws.slug(key)}", sections,
                                  [{"label": "Add a scene", "say": f"Add a scene to the plot of {key}."}]))


def scene_delete(settings: Settings, args: dict) -> screen.Shown | str:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    i = scene_index(p, args.get("name"))
    ask = confirm_first(f"the scene {p['scenes'][i]['title']}", args)
    if ask:
        return ask
    scene = p["scenes"].pop(i)
    ws.save(settings, data)
    return scene_list(settings, {"project": key}, f"Deleted the scene {scene['title']}.") if p["scenes"] else \
        f"Deleted the scene {scene['title']}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "writing_story_bible",
        "description": "A story's bible for a writing project. Character bible: character_add (or update: name, "
                       "role, traits, appearance, notes), character_list, character_card (one character), "
                       "character_delete. World and setting notes: world_add (a place or lore entry), world_list, "
                       "world_delete. Plot planner: scene_add (act 1, 2 or 3), scene_move (reorder, or to another "
                       "act), scene_list (scenes by act), scene_delete. Deletes: confirmed true only after the user "
                       "says yes. Project defaults to the one last used.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "project": {"type": "string"},
                "name": {"type": "string", "description": "Character, place/lore entry or scene title."},
                "role": {"type": "string"},
                "traits": {"type": "string"},
                "appearance": {"type": "string"},
                "notes": {"type": "string", "description": "Character notes, world notes or what happens in the scene."},
                "type": {"type": "string", "enum": WORLD_TYPES},
                "act": {"type": "integer", "enum": [1, 2, 3]},
                "position": {"type": "integer", "description": "Scene's place within its act, 1 = first."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"writing_story_bible"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handler = {"character_add": character_add, "character_list": character_list, "character_card": character_card,
               "character_delete": character_delete, "world_add": world_add, "world_list": world_list,
               "world_delete": world_delete, "scene_add": scene_add, "scene_move": scene_move,
               "scene_list": scene_list, "scene_delete": scene_delete}.get(args.get("action"))
    if not handler:
        raise ValueError(f"Unknown action {args.get('action')}.")
    return handler(settings, args)
