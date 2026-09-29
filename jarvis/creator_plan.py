"""Creator ideas, part 4: the series planner (episode lists that track what is done), trend notes that expire after 14
days, the swipe file of examples that worked, and comment reply ideas.

Trend notes are typed in by the user: nothing is fetched from any platform. Kept in creatorideas.json in the memory
folder. Reply ideas are written by Alfred from the comment the user pastes in.
"""

from datetime import datetime, timedelta

import homestore as hs
import screen
import creator_store as store
from config import Settings

ACTIONS = ["series_new", "series_show", "series_list", "series_done", "series_remove", "trend_add", "trend_list",
           "trend_remove", "trend_angles", "swipe_add", "swipe_list", "swipe_remove", "comment_reply"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
ZODIAC = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn",
          "Aquarius", "Pisces"]
TEMPLATES = {
    "birth month": [f"Born in {m}" for m in MONTHS],
    "letter": [f"The letter {chr(65 + n)}" for n in range(26)],
    "zodiac": ZODIAC,
    "weekday": [f"Born on a {d.title()}" for d in hs.WEEKDAYS],
}


def _episodes(args: dict, name: str) -> list[str]:
    given = store.texts(args.get("episodes"), 80)
    if given:
        return given[:60]
    lowered = name.lower()
    for key, titles in TEMPLATES.items():
        if key in lowered or (key == "weekday" and "day" in lowered and "born" in lowered):
            return list(titles)
    count = int(hs.number(args.get("count") or 0, "number of parts", 0, 60))
    if not count:
        raise ValueError("Give me the episode titles, or how many parts, or a name like Birth Months or "
                         "Letter Psychology.")
    return [f"Part {n} of {count}" for n in range(1, count + 1)]


def _series(data: dict, name) -> str:
    key = hs.find(data["series"], hs.need(name, "series"))
    if key is None:
        have = f" I have: {', '.join(data['series'])}." if data["series"] else ""
        raise ValueError(f"I don't have a series called {hs.clean(name)}.{have}")
    return key


def series_new(settings: Settings, args: dict) -> screen.Shown:
    name = hs.need(args.get("name"), "series name", 60)
    data = store.load(settings)
    if len(data["series"]) >= 20 and name not in data["series"]:
        raise ValueError("You have too many series; remove one first.")
    titles = _episodes(args, name)
    data["series"][name] = {"account": hs.clean(args.get("account"), 40),
                            "episodes": [{"title": t, "done": False} for t in titles]}
    store.save(settings, data)
    shown = _show(name, data["series"][name])
    return screen.Shown(f"Planned {name}: {len(titles)} episodes. Say which one you finish and I'll tick it off.",
                        shown.card)


def _show(name: str, series: dict) -> screen.Shown:
    eps = series["episodes"]
    done = sum(1 for e in eps if e["done"])
    items = [{"label": f"{n}. {e['title']}", "done": e["done"],
              "say": f"Mark episode {n} of {name} as done."} for n, e in enumerate(eps, 1)]
    return screen.Shown(f"{name}: {done} of {len(eps)} episodes done.",
                        screen.card("list", f"{name} ({done}/{len(eps)})", "creator-series-" + name.lower()[:30],
                                    items=items, checks=True))


def series_show(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    name = _series(data, args.get("name"))
    return _show(name, data["series"][name])


def series_list(settings: Settings, args: dict) -> screen.Shown | str:
    data = store.load(settings)
    if not data["series"]:
        return "You haven't planned any series yet. Try Birth Months or Letter Psychology."
    rows = [[n, str(sum(e["done"] for e in s["episodes"])), str(len(s["episodes"])), s["account"]]
            for n, s in data["series"].items()]
    return screen.Shown(f"You have {len(rows)} series.",
                        screen.card("table", "Series", "creator-serieslist",
                                    columns=["Series", "Done", "Episodes", "Account"], rows=rows))


def series_done(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    name = _series(data, args.get("name"))
    eps = data["series"][name]["episodes"]
    wanted = args.get("episode")
    if isinstance(wanted, int) or str(wanted).isdigit():
        index = int(wanted) - 1
    else:
        index = next((n for n, e in enumerate(eps) if hs.clean(wanted).lower() in e["title"].lower()), -1) \
            if hs.clean(wanted) else -1
    if not 0 <= index < len(eps):
        raise ValueError("Which episode? Give its number or part of its title.")
    eps[index]["done"] = args.get("undo") is not True
    store.save(settings, data)
    shown = _show(name, data["series"][name])
    left = next((e["title"] for e in eps if not e["done"]), None)
    return screen.Shown(f"{eps[index]['title']} is {'done' if eps[index]['done'] else 'not done'}. "
                        + (f"Next up: {left}." if left else "The series is finished."), shown.card)


def series_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    name = _series(data, args.get("name"))
    if not args.get("confirmed"):
        return store.confirm_needed(f"the series {name}")
    del data["series"][name]
    store.save(settings, data)
    return f"Removed the series {name}."


# ---- Trend notes ---------------------------------------------------------------------------------

def _live_trends(data: dict, when: datetime) -> list[dict]:
    cutoff = (when - timedelta(days=store.TREND_DAYS)).strftime("%Y-%m-%d")
    return [t for t in data["trends"] if t["added"] > cutoff]


def trend_add(settings: Settings, args: dict, when: datetime) -> str:
    data = store.load(settings)
    data["trends"] = _live_trends(data, when)
    kind = hs.clean(args.get("kind")).lower() or "sound"
    store.put(data["trends"], {"text": hs.need(args.get("text"), "trend", 150), "kind": kind[:20],
                               "added": when.strftime("%Y-%m-%d")}, 60)
    store.save(settings, data)
    return f"Noted. Trend notes disappear after {store.TREND_DAYS} days."


def trend_list(settings: Settings, args: dict, when: datetime) -> screen.Shown | str:
    data = store.load(settings)
    live = _live_trends(data, when)
    if len(live) != len(data["trends"]):
        data["trends"] = live
        store.save(settings, data)
    if not live:
        return "No current trend notes. They expire after 14 days; tell me a sound or format you've spotted."
    rows = [[str(n), t["kind"], t["text"], t["added"],
             f"{store.TREND_DAYS - (when.date() - datetime.strptime(t['added'], '%Y-%m-%d').date()).days} days"]
            for n, t in enumerate(live, 1)]
    return screen.Shown(f"{len(rows)} trend note{'s' if len(rows) != 1 else ''} still fresh.",
                        screen.card("table", "Trend notes", "creator-trends",
                                    columns=["#", "Kind", "Note", "Added", "Left"], rows=rows))


def trend_remove(settings: Settings, args: dict, when: datetime) -> str:
    data = store.load(settings)
    live = _live_trends(data, when)
    try:
        gone = live.pop(int(args.get("number")) - 1)
    except (TypeError, ValueError, IndexError):
        raise ValueError("Which trend number? Ask me to list them first.") from None
    data["trends"] = live
    store.save(settings, data)
    return f"Removed the note {gone['text']}."


def trend_angles(settings: Settings, args: dict) -> str:
    words = store.texts(args.get("keywords") or args.get("text"), 40)[:8]
    if not words:
        raise ValueError("Which keywords should I brainstorm from?")
    account = hs.clean(args.get("account"), 40)
    data = store.load(settings)
    key = hs.find(data["pillars"], account) if account else None
    pillars = data["pillars"].get(key, []) if key else []
    live = [t["text"] for t in _live_trends(data, store.now(None))][:8]
    return (f"Keywords: {', '.join(words)}. Pillars: {', '.join(pillars) or 'none set'}. The user's own trend notes: "
            f"{'; '.join(live) or 'none'}. Write six fresh angles for short videos that link these keywords to the "
            "account, one line each, each with a different format (story, list, myth vs fact, POV, question, "
            "comparison). Nothing is looked up online, so do not claim any of it is trending; these are "
            "brainstorm angles only. Offer to save the best as ideas.")


# ---- Swipe file ----------------------------------------------------------------------------------

def swipe_add(settings: Settings, args: dict, when: datetime) -> str:
    data = store.load(settings)
    entry = {"title": hs.need(args.get("title") or args.get("text"), "example", 150),
             "why": hs.clean(args.get("why"), 300), "link": hs.clean(args.get("link"), 300),
             "tags": store.texts(args.get("tags"), 30)[:6], "added": when.strftime("%Y-%m-%d")}
    store.put(data["swipe"], entry)
    store.save(settings, data)
    return f"Saved to your swipe file ({len(data['swipe'])} examples)."


def swipe_list(settings: Settings, args: dict) -> screen.Shown | str:
    query = hs.clean(args.get("query")).lower()
    found = [(n, s) for n, s in enumerate(store.load(settings)["swipe"], 1)
             if not query or query in f"{s['title']} {s['why']} {' '.join(s['tags'])}".lower()]
    if not found:
        return "Nothing in your swipe file" + (" matches that." if query else " yet. Save an example that worked.")
    rows = [[str(n), s["title"], s["why"], ", ".join(s["tags"])] for n, s in found]
    return screen.Shown(f"{len(rows)} example{'s' if len(rows) != 1 else ''} in your swipe file.",
                        screen.card("table", "Swipe file", "creator-swipe",
                                    columns=["#", "Example", "Why it worked", "Tags"], rows=rows))


def swipe_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    try:
        entry = data["swipe"][int(args.get("number")) - 1]
    except (TypeError, ValueError, IndexError):
        raise ValueError("Which swipe file number?") from None
    if not args.get("confirmed"):
        return store.confirm_needed(f"the example {entry['title']}")
    data["swipe"].remove(entry)
    store.save(settings, data)
    return f"Removed {entry['title']} from your swipe file."


# ---- Comment replies -----------------------------------------------------------------------------

def comment_reply(settings: Settings, args: dict) -> str:
    comment = hs.need(args.get("comment"), "comment", 500)
    account = hs.clean(args.get("account"), 40)
    pillars = store.load(settings)["pillars"].get(hs.find(store.load(settings)["pillars"], account) or "", [])
    return (f"The comment: \"{comment}\". Account: {account or 'not given'}; pillars: {', '.join(pillars) or 'none'}. "
            "Write three short reply options (friendly, funny, curious) in the account's voice, each under 150 "
            "characters, that invite another comment. Then offer one idea for a reply video that answers the "
            "comment. Don't argue with rude comments; suggest ignoring or hiding those. Nothing is posted; the "
            "user copies the reply themselves.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_plan",
        "description": "Planning for short-video accounts. action: series_new (name like Birth Months / Letter "
                       "Psychology / Zodiac, or episodes, or count, account) = episode list / series_show / "
                       "series_list / series_done (name, episode number or title, undo) / series_remove (name, "
                       "confirmed only after yes); trend_add (text, kind sound/format) / trend_list / trend_remove "
                       "(number) = the user's own trend notes, they expire after 14 days; swipe_add (title, why, "
                       "tags) / swipe_list (query) / swipe_remove (number, confirmed) = saved examples and why "
                       "they worked; comment_reply (comment, account) = returns the comment for YOU to write "
                       "reply options; trend_angles (keywords, account) = brainstorm angles from words the user gives, "
                       "returns notes for YOU to write. Never posts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "Series name."},
                "episodes": {"type": "array", "items": {"type": "string"}},
                "count": {"type": "integer", "description": "series_new: number of parts."},
                "episode": {"type": "string", "description": "series_done: number or part of the title."},
                "undo": {"type": "boolean"},
                "account": {"type": "string"},
                "text": {"type": "string", "description": "trend_add: the sound or format."},
                "kind": {"type": "string"},
                "number": {"type": "integer", "description": "trend or swipe file entry number."},
                "title": {"type": "string"},
                "why": {"type": "string", "description": "swipe_add: why it worked."},
                "link": {"type": "string", "description": "swipe_add: where it is, only stored."},
                "tags": {"type": "array", "items": {"type": "string"}},
                "query": {"type": "string"},
                "comment": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "trend_angles: the words."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"creator_plan"}


def run_tool(name: str, args: dict, settings: Settings, http=None, now=None):
    when = store.now(now)
    action = args.get("action")
    plain = {"series_new": series_new, "series_show": series_show, "series_list": series_list,
             "series_done": series_done, "series_remove": series_remove, "swipe_list": swipe_list,
             "swipe_remove": swipe_remove, "comment_reply": comment_reply, "trend_angles": trend_angles}
    timed = {"trend_add": trend_add, "trend_list": trend_list, "trend_remove": trend_remove, "swipe_add": swipe_add}
    if action in plain:
        return plain[action](settings, args)
    if action in timed:
        return timed[action](settings, args, when)
    raise ValueError("I can't do that one.")
