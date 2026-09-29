"""Everyday support, part 2: important people with photos ("who is Sam?"), step-by-step guides shown one big step
at a time (how to use the washing machine) and plain-language explanations of letters and bills.

People and guides are kept in support.json in the memory folder; photos are files already in the memory folders.
New pop-up kinds: "support-people" and "support-steps", drawn by popup-support.js.
"""

from urllib.parse import quote

import homestore as hs
import memory
import screen
import support_store as store
from config import Settings

screen.EXTRA_KINDS.update({"support-people", "support-steps"})
ACTIONS = ["people_add", "people_who", "people_list", "people_remove", "guide_save", "guide_show", "guide_list",
           "guide_delete", "letter"]
TEXT_FILES = {".txt", ".md", ".csv"}
MAX_LETTER = 6000


def _photo(settings: Settings, value) -> str:
    """The memory-folder path of a photo ('Personal/sam.jpg'), or '' when none was given."""
    text = hs.clean(value, 200)
    if not text:
        return ""
    return screen.memory_path(settings, text).relative_to(memory.root(settings).resolve()).as_posix()


def _src(settings: Settings, rel: str) -> str:
    try:
        screen.memory_path(settings, rel)
    except ValueError:
        return ""
    return f"/screen/file?path={quote(rel)}" if rel else ""


def _person(settings: Settings, name: str, info: dict) -> dict:
    return {"name": name, "relation": info.get("relation", ""), "note": info.get("note", ""),
            "src": _src(settings, info.get("photo", ""))}


def people_add(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "person")
    data = store.load(settings)
    key = next((k for k in data["people"] if k.lower() == name.lower()), name)
    if key not in data["people"] and len(data["people"]) >= store.MAX_ITEMS:
        raise ValueError("The people list is full; remove someone first.")
    info = dict(data["people"].get(key, {}))
    for field, limit in (("relation", 60), ("note", 200)):
        if args.get(field) is not None:
            info[field] = hs.clean(args[field], limit)
    if args.get("photo"):
        info["photo"] = _photo(settings, args["photo"])
    data["people"][key] = info
    store.save(settings, data)
    return f"Saved {key}" + (f", your {info['relation']}." if info.get("relation") else ".")


def people_who(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    wanted = hs.need(args.get("name"), "person").lower()
    found = [k for k, v in data["people"].items()
             if wanted in k.lower() or wanted in v.get("relation", "").lower()]
    if not found:
        raise ValueError(f"I don't have anyone called {wanted} saved. Tell me who they are and I'll remember.")
    people = [_person(settings, k, data["people"][k]) for k in found]
    c = screen.card("support-people", people[0]["name"] if len(people) == 1 else "Who is who", "support-who",
                    data={"people": people})
    first = people[0]
    said = f"{first['name']} is your {first['relation']}." if first["relation"] else f"{first['name']} is someone you know."
    return screen.Shown(said + (f" {first['note']}" if first["note"] else ""), c)


def people_list(settings: Settings) -> screen.Shown:
    data = store.load(settings)
    if not data["people"]:
        return screen.Shown("You haven't saved any important people yet.", screen.card(
            "text", "Important people", "support-people-empty", text="Nobody saved yet."))
    people = [_person(settings, k, v) for k, v in data["people"].items()]
    c = screen.card("support-people", "Important people", "support-people", data={"people": people})
    return screen.Shown(f"You have {len(people)} important people: " + ", ".join(p["name"] for p in people[:8]) + ".", c)


def people_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    key = store.match(data["people"], args.get("name"), "person")
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing {key}, then call again with confirmed true."
    del data["people"][key]
    store.save(settings, data)
    return f"Removed {key}."


def guide_save(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "guide", 60)
    steps = [hs.clean(s, 200) for s in args.get("steps") or [] if hs.clean(s)]
    if not steps:
        raise ValueError("What are the steps? Say them in order.")
    data = store.load(settings)
    key = next((k for k in data["guides"] if k.lower() == name.lower()), name)
    if key not in data["guides"] and len(data["guides"]) >= store.MAX_ITEMS:
        raise ValueError("There are too many guides; delete one first.")
    data["guides"][key] = steps[:store.MAX_ITEMS]
    store.save(settings, data)
    return f"Saved the guide {key}: {len(steps[:store.MAX_ITEMS])} steps."


def guide_show(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    key = store.match(data["guides"], args.get("name"), "guide")
    steps = data["guides"][key]
    start = min(max(int(args.get("step") or 1), 1), len(steps)) - 1
    c = screen.card("support-steps", key, f"support-guide-{key}", data={"title": key, "steps": steps, "index": start})
    return screen.Shown(f"Step {start + 1} of {len(steps)}: {steps[start]}", c)


def guide_list(settings: Settings) -> screen.Shown | str:
    guides = store.load(settings)["guides"]
    if not guides:
        return "You haven't saved any guides yet. Tell me a name and the steps."
    items = [{"label": f"{k} ({len(v)} steps)", "say": f"Show me the guide {k}."} for k, v in guides.items()]
    return screen.Shown(f"You have {len(guides)} guides: " + ", ".join(guides) + ".",
                        screen.card("list", "My step-by-step guides", "support-guides", items=items))


def guide_delete(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    key = store.match(data["guides"], args.get("name"), "guide")
    if not args.get("confirmed"):
        return f"Ask the user to confirm deleting the guide {key}, then call again with confirmed true."
    del data["guides"][key]
    store.save(settings, data)
    return f"Deleted the guide {key}."


def letter(settings: Settings, args: dict) -> str:
    text = str(args.get("text") or "").strip()
    if not text and args.get("filename"):
        path = screen.find_file(settings, hs.clean(args.get("folder")), hs.clean(args.get("filename"), 200))
        if path.suffix.lower() not in TEXT_FILES:
            raise ValueError(f"I can only read {path.name} from a text file. Read me the words or paste them in.")
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        raise ValueError("Read me the letter, or tell me which text file it is in.")
    return ("Explain this letter or bill in very plain, short sentences, as if to a friend: who it is from, what it "
            "says, whether anything must be done and by when, and what it costs. Do not guess; say if something is "
            "unclear, and suggest asking someone they trust before paying or replying.\n\nLETTER:\n" + text[:MAX_LETTER])


def tool_definitions() -> list[dict]:
    return [{
        "name": "support_people",
        "description": "Helps people who forget or find things hard. action: people_add (name, relation, note, "
                       "photo = 'Folder/file.jpg' in the memory folders) / people_who = 'who is Sam?' or 'who is my "
                       "daughter?' with photo / people_list / people_remove (confirmed true only after the user says "
                       "yes); guide_save (name, steps in order) = a step-by-step how-to such as using the washing "
                       "machine / guide_show (name, optional step) = one big step at a time with Next and Back / "
                       "guide_list / guide_delete (confirmed true only after the user says yes); letter = explain a "
                       "letter or bill in plain words (text, or folder and filename of a text file).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "A person's name or relationship, or a guide's name."},
                "relation": {"type": "string", "description": "people_add: e.g. daughter, neighbour, GP."},
                "note": {"type": "string"},
                "photo": {"type": "string", "description": "people_add: a picture in the memory folders."},
                "steps": {"type": "array", "items": {"type": "string"}},
                "step": {"type": "integer", "description": "guide_show: the step to start at, from 1."},
                "text": {"type": "string", "description": "letter: the words of the letter."},
                "folder": {"type": "string"},
                "filename": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"support_people"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "people_list":
        return people_list(settings)
    if action == "guide_list":
        return guide_list(settings)
    actions = {"people_add": people_add, "people_who": people_who, "people_remove": people_remove,
               "guide_save": guide_save, "guide_show": guide_show, "guide_delete": guide_delete, "letter": letter}
    if action not in actions:
        raise ValueError("I can't do that one.")
    return actions[action](settings, args)
