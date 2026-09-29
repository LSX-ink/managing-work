"""Reading help: a big-text reader pop-up that reads a web page, pasted words or a text file aloud.

The reading itself happens in the browser (frontend/popup-webread.js): paragraph by paragraph with the voice
chosen in Alfred's voice picker, the current paragraph highlighted, pause, skip and speed, plus a reading ruler,
text size, line spacing and background tints. Alfred only says one short sentence. Where you stopped (per link
or file) and your reader look are kept in reading.json (webread_store.py). Page fetching is webread_extract.py.
"""

import json

import httpx

import screen
import webread_extract as ex
import webread_store as store
from config import Settings

screen.EXTRA_KINDS.add("webread-reader")

ACTIONS = ["page", "text", "file", "resume", "save_place", "places", "forget_place", "look"]
READING_WPM = 200
MAX_READER_JSON = 190_000


def minutes(blocks: list[dict]) -> int:
    return max(1, round(sum(len(b["t"].split()) for b in blocks) / READING_WPM))


def start_index(blocks: list[dict], args: dict, saved: int = 0) -> int:
    heading = str(args.get("from_heading") or "").strip().lower()
    if heading:
        for i, b in enumerate(blocks):
            if b["k"].startswith("h") and heading in b["t"].lower():
                return i
        raise ValueError(f"I couldn't find a heading called {args['from_heading']} on it.")
    if args.get("from_paragraph"):
        return min(len(blocks), max(1, int(args["from_paragraph"]))) - 1
    return min(saved, len(blocks) - 1)


def reader_card(settings: Settings, page: dict, start: int = 0) -> screen.Shown:
    blocks = page["blocks"][:]
    data = {"title": page["title"], "site": page.get("site", ""), "url": page.get("url", ""),
            "folder": page.get("folder", ""), "filename": page.get("filename", ""), "start": start,
            "prefs": store.load(settings)["prefs"]}
    while True:
        data["paras"] = [{"t": b["t"], "h": b["k"].startswith("h")} for b in blocks]
        if len(json.dumps(data)) <= MAX_READER_JSON or len(blocks) <= start + 1:
            break
        blocks.pop()
    buttons = []
    if page.get("url"):
        buttons = [{"label": "Simple version", "say": f"Make {page['url']} simple to read."},
                   {"label": "Summary", "say": f"Summarise {page['url']} in three bullet points."}]
    card = screen.card("webread-reader", page["title"], f"webread-{store.key_for(page.get('url'), page.get('folder'), page.get('filename')) or page['title']}",
                       data=data, buttons=buttons)
    where = f" from paragraph {start + 1}" if start else ""
    return screen.Shown(f"{page['title']} is in the reader{where}, about {minutes(blocks)} minutes; press Read aloud.", card)


async def read(settings: Settings, http: httpx.AsyncClient, args: dict) -> screen.Shown:
    page = await ex.source(settings, http, args)
    return reader_card(settings, page, start_index(page["blocks"], args))


def save_place(settings: Settings, args: dict) -> str:
    key = store.key_for(args.get("url"), args.get("folder"), args.get("filename"))
    if not key:
        raise ValueError("Which page or file should I remember your place in?")
    index = max(1, int(args.get("index") or 1))
    total = max(index, int(args.get("total") or index))
    kind = "page" if args.get("url") else "file"
    title = str(args.get("title") or key).strip()
    store.remember(settings, key, title, index - 1, total, kind, str(args.get("folder") or ""), str(args.get("filename") or ""))
    return f"Saved. I'll remember you stopped {title} at paragraph {index} of {total}."


async def resume(settings: Settings, http: httpx.AsyncClient, args: dict) -> screen.Shown:
    found = store.find(store.load(settings), args.get("url") or args.get("title") or args.get("filename") or "")
    if not found:
        raise ValueError("I haven't got a saved place" + (" for that." if args.get("url") or args.get("title") else " yet."))
    key, place = found
    if place["kind"] == "page":
        page = await ex.fetch_page(http, key)
    else:
        page = ex.read_file(settings, place.get("folder", ""), place.get("filename", ""))
    page["title"] = page["title"] or place["title"]
    shown = reader_card(settings, page, start_index(page["blocks"], args, place["index"]))
    return screen.Shown(f"Picking up {page['title']} at paragraph {place['index'] + 1} of {place['total']}.", shown.card)


def places(settings: Settings) -> screen.Shown:
    data = store.load(settings)["places"]
    if not data:
        return screen.Shown("You haven't saved a place in anything yet.", screen.card(
            "text", "Where you stopped", "webread-places", text="Press Save my place in the reader to remember where you stopped."))
    ranked = sorted(data.values(), key=lambda p: p.get("at", ""), reverse=True)
    items = [{"label": f"{p['title']}: paragraph {p['index'] + 1} of {p['total']}",
              "say": f"Carry on reading {p['title']}."} for p in ranked]
    card = screen.card("list", "Where you stopped", "webread-places", items=items)
    return screen.Shown(f"You have {len(ranked)} saved places; the latest is {ranked[0]['title']}. Tap one to carry on.", card)


def forget_place(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    found = store.find(data, args.get("url") or args.get("title") or args.get("filename") or "")
    if not found:
        raise ValueError("I haven't got a saved place for that.")
    key, place = found
    if not args.get("confirmed"):
        return f"Ask the user to confirm forgetting their place in {place['title']}, then call again with confirmed true."
    del data["places"][key]
    store.save(settings, data)
    return f"Forgot your place in {place['title']}."


def look(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    data["prefs"] = store.clamp_prefs(args, data["prefs"])
    store.save(settings, data)
    p = data["prefs"]
    text = (f"Text size {p['size']}, line spacing {p['spacing']}, {p['tint']} background, "
            f"ruler {'on' if p['ruler'] else 'off'}, reading speed {p['speed']}.")
    return screen.Shown("Saved. The reader will open like that from now on.",
                        screen.card("text", "Reader look", "webread-look", text=text))


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_read_aloud",
        "description": "Reading aid: read a public web page, pasted text or a .txt/.md file from the memory folders "
                       "aloud in a big-text reader pop-up (paragraph by paragraph, highlighted, pause, skip, speed, "
                       "reading ruler, text size, tints). page: a link (optionally from_heading or from_paragraph); "
                       "text: pasted words; file: folder + filename; resume: carry on where they stopped; "
                       "save_place: remember they stopped at paragraph index of total (the reader's Save my place "
                       "button says so); places: list saved places; forget_place: only with confirmed true after the "
                       "user agrees; look: save their reader size, spacing, tint, ruler or speed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "url": {"type": "string", "description": "page, resume, save_place, forget_place: the link."},
                "text": {"type": "string", "description": "text: the words to read."},
                "title": {"type": "string", "description": "text: a name; resume, forget_place, save_place: title of the page."},
                "folder": {"type": "string", "description": "file: memory folder, e.g. 'Ideas'."},
                "filename": {"type": "string", "description": "file: its name, or part of it."},
                "from_heading": {"type": "string", "description": "start at the heading containing these words."},
                "from_paragraph": {"type": "integer", "description": "start at this paragraph number (1 is the first)."},
                "index": {"type": "integer", "description": "save_place: the paragraph they stopped at (1 is the first)."},
                "total": {"type": "integer", "description": "save_place: how many paragraphs there are."},
                "size": {"type": "integer", "description": "look: text size 14 to 48."},
                "spacing": {"type": "number", "description": "look: line spacing 1.2 to 2.6."},
                "tint": {"type": "string", "enum": store.TINTS, "description": "look: reader background."},
                "ruler": {"type": "boolean", "description": "look: reading ruler on or off."},
                "speed": {"type": "number", "description": "look: reading speed 0.6 (slow) to 1.6 (fast)."},
                "confirmed": {"type": "boolean", "description": "forget_place: true only after the user confirms."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"web_read_aloud"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    action = args.get("action")
    if action in ("page", "text", "file"):
        return await read(settings, http, args)
    if action == "resume":
        return await resume(settings, http, args)
    if action == "save_place":
        return save_place(settings, args)
    if action == "places":
        return places(settings)
    if action == "forget_place":
        return forget_place(settings, args)
    if action == "look":
        return look(settings, args)
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
