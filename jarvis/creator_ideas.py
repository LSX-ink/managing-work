"""Creator ideas, part 1: content pillars per account, the idea bank (tags, status, search), the idea generator, past
winners and the brainstorm board.

Planning only, kept in creatorideas.json in the memory folder; nothing is posted or sent anywhere. The generator does
not invent ideas itself: it returns the niche, pillars and past winners with an instruction for Alfred to write them,
then idea_save stores the ones the user picks. New pop-up kind: "creator-board" (columns idea, scripted, ready),
drawn by popup-creatorideas.js.
"""

import homestore as hs
import screen
import creator_store as store
from config import Settings

screen.EXTRA_KINDS.add("creator-board")
ACTIONS = ["pillar_add", "pillar_list", "pillar_remove", "idea_add", "idea_save", "idea_list", "idea_search",
           "idea_status", "idea_remove", "idea_generate", "winner_mark", "board"]
COLUMNS = ["idea", "scripted", "ready"]


def _account(args: dict, required: bool = True) -> str:
    return hs.need(args.get("account"), "account") if required else hs.clean(args.get("account"), 40)


def _match(text: str, query: str) -> bool:
    return all(w in text.lower() for w in query.lower().split())


def _find(data: dict, args: dict) -> dict:
    try:
        wanted = int(args.get("id"))
    except (TypeError, ValueError):
        raise ValueError("Which idea number?") from None
    idea = next((i for i in data["ideas"] if i["id"] == wanted), None)
    if idea is None:
        raise ValueError(f"I don't have idea number {wanted}.")
    return idea


def _new_idea(data: dict, text, account: str, tags, when) -> dict:
    idea = {"id": data["next_id"], "text": hs.need(text, "idea", 200), "account": account,
            "tags": store.texts(tags, 30)[:6], "status": "idea", "winner": False,
            "added": when.strftime("%Y-%m-%d")}
    data["next_id"] += 1
    store.put(data["ideas"], idea)
    return idea


# ---- Pillars -------------------------------------------------------------------------------------

def pillar_add(settings: Settings, args: dict) -> str:
    account = _account(args)
    new = store.texts(args.get("pillars") or args.get("text"))
    if not new:
        raise ValueError("Which pillar or pillars? For example: true stories, psychology facts, dark history.")
    data = store.load(settings)
    have = data["pillars"].setdefault(account, [])
    for p in new:
        if p.lower() not in [h.lower() for h in have]:
            store.put(have, p, 12)
    store.save(settings, data)
    return f"{account} now has {len(have)} pillars: {', '.join(have)}."


def pillar_list(settings: Settings, args: dict) -> screen.Shown | str:
    data = store.load(settings)
    wanted = _account(args, False)
    accounts = {a: p for a, p in data["pillars"].items() if not wanted or wanted.lower() in a.lower()}
    if not accounts:
        return "You haven't set any content pillars yet. Tell me the account and its pillars."
    rows = [[a, ", ".join(p)] for a, p in accounts.items()]
    return screen.Shown(f"Pillars for {len(rows)} account{'s' if len(rows) != 1 else ''}.",
                        screen.card("table", "Content pillars", "creator-pillars", columns=["Account", "Pillars"],
                                    rows=rows))


def pillar_remove(settings: Settings, args: dict) -> str:
    account = _account(args)
    data = store.load(settings)
    key = hs.find(data["pillars"], account)
    if key is None:
        raise ValueError(f"I don't have pillars for {account}.")
    gone = hs.find(data["pillars"][key], hs.need(args.get("text") or args.get("pillar"), "pillar"))
    if gone is None:
        raise ValueError(f"{key} has no pillar like that.")
    data["pillars"][key].remove(gone)
    store.save(settings, data)
    return f"Removed the pillar {gone} from {key}."


# ---- Idea bank -----------------------------------------------------------------------------------

def idea_add(settings: Settings, args: dict, when) -> str:
    data = store.load(settings)
    idea = _new_idea(data, args.get("text"), _account(args, False), args.get("tags"), when)
    store.save(settings, data)
    return f"Saved idea {idea['id']}: {idea['text']}"


def idea_save(settings: Settings, args: dict, when) -> str:
    items = store.texts(args.get("ideas"), 200)
    if not items:
        raise ValueError("Which ideas should I save?")
    data = store.load(settings)
    for text in items[:20]:
        _new_idea(data, text, _account(args, False), args.get("tags"), when)
    store.save(settings, data)
    return f"Saved {min(len(items), 20)} ideas to your idea bank."


def _idea_table(ideas: list[dict], title: str, card_id: str) -> screen.Shown | str:
    if not ideas:
        return "No ideas match."
    rows = [[str(i["id"]), i["text"], i["status"] + (" *" if i.get("winner") else ""), ", ".join(i["tags"])]
            for i in ideas[:60]]
    more = f" Showing the first {len(rows)}." if len(ideas) > len(rows) else ""
    return screen.Shown(f"{len(ideas)} idea{'s' if len(ideas) != 1 else ''}.{more}",
                        screen.card("table", title, card_id, columns=["#", "Idea", "Status", "Tags"], rows=rows))


def idea_list(settings: Settings, args: dict) -> screen.Shown | str:
    ideas = store.load(settings)["ideas"]
    status = hs.clean(args.get("status")).lower()
    if status and status not in store.STATUSES:
        raise ValueError(f"Status can be {', '.join(store.STATUSES)}.")
    account = _account(args, False).lower()
    found = [i for i in ideas if (not status or i["status"] == status) and (not account or account in i["account"].lower())]
    if not found:
        return "Your idea bank is empty. Tell me an idea, or ask me to come up with some."
    return _idea_table(found, "Idea bank", "creator-ideas")


def idea_search(settings: Settings, args: dict) -> screen.Shown | str:
    query = hs.clean(args.get("query") or args.get("text"))
    tag = store.tag(args.get("tag")) if args.get("tag") else ""
    if not query and not tag:
        raise ValueError("What should I search for?")
    found = [i for i in store.load(settings)["ideas"]
             if _match(f"{i['text']} {i['account']} {' '.join(i['tags'])}", query)
             and (not tag or tag in [store.tag(t) for t in i["tags"]])]
    return _idea_table(found, f"Ideas: {query or '#' + tag}", "creator-search")


def idea_status(settings: Settings, args: dict) -> str:
    status = hs.clean(args.get("status")).lower()
    if status not in store.STATUSES:
        raise ValueError(f"Status can be {', '.join(store.STATUSES)}.")
    data = store.load(settings)
    idea = _find(data, args)
    idea["status"] = status
    store.save(settings, data)
    return f"Idea {idea['id']} is now {status}."


def idea_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    idea = _find(data, args)
    if not args.get("confirmed"):
        return store.confirm_needed(f"idea {idea['id']}: {idea['text']}")
    data["ideas"].remove(idea)
    store.save(settings, data)
    return f"Removed idea {idea['id']}."


def winner_mark(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    idea = _find(data, args)
    idea["winner"] = args.get("winner") is not False
    if idea["winner"]:
        idea["status"] = "used"
    store.save(settings, data)
    return f"Idea {idea['id']} is {'marked as a winner' if idea['winner'] else 'no longer a winner'}."


# ---- Generator and board -------------------------------------------------------------------------

def idea_generate(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    niche = hs.need(args.get("niche") or args.get("account"), "niche")
    count = max(3, min(int(hs.number(args.get("count") or 10, "number of ideas", 1, 30)), 30))
    key = hs.find(data["pillars"], niche)
    pillars = data["pillars"].get(key, []) if key else []
    winners = [i["text"] for i in data["ideas"] if i.get("winner")][:8]
    taken = [i["text"] for i in data["ideas"]][-25:]
    return (f"Niche: {niche}. Pillars: {', '.join(pillars) or 'none set yet (suggest some and offer to save them)'}. "
            f"Past winners: {'; '.join(winners) or 'none yet'}. Already in the bank (do not repeat): "
            f"{'; '.join(taken) or 'nothing'}. Write {count} fresh short-form video ideas for this niche as one "
            "punchy line each, mixing the pillars and echoing what worked in the winners. Keep them honest (no "
            "made-up news, no income promises). Read the best few aloud, then ask which to save; save the picked "
            "ones with idea_save.")


def _board_column(name: str, ideas: list[dict]) -> dict:
    later = COLUMNS[COLUMNS.index(name) + 1] if name != COLUMNS[-1] else "used"
    return {"name": name, "next": later,
            "items": [{"id": i["id"], "text": i["text"], "tags": i["tags"], "say": f"Move idea {i['id']} to {later}."}
                      for i in ideas if i["status"] == name]}


def board(settings: Settings, args: dict) -> screen.Shown | str:
    account = _account(args, False).lower()
    ideas = [i for i in store.load(settings)["ideas"] if not account or account in i["account"].lower()]
    if not ideas:
        return "The board is empty. Add some ideas first."
    columns = [_board_column(n, ideas) for n in COLUMNS]
    counts = ", ".join(f"{c['name']} {len(c['items'])}" for c in columns)
    counts = ", ".join(f"{len(c['items'])} {c['name']}" for c in columns)
    return screen.Shown(f"Your board: {counts}.",
                        screen.card("creator-board", "Content board", "creator-board", data={"columns": columns}))


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_ideas",
        "description": "Content ideas for faceless short-form accounts (TikTok, Reels, Shorts). Planning only, never "
                       "posts. action: pillar_add (account, pillars) / pillar_list / pillar_remove (account, text) = "
                       "content pillars per account; idea_add (text, tags, account) / idea_save (ideas = the ones "
                       "the user picked) / idea_list (status, account) / idea_search (query or tag) / idea_status "
                       "(id, status idea|scripted|ready|used) / idea_remove (id, confirmed only after yes) / "
                       "winner_mark (id) = idea bank; idea_generate (niche or account, count) = 'give me video "
                       "ideas': returns pillars and past winners, then YOU write the ideas and save picks with "
                       "idea_save; board = pop-up idea to scripted to ready columns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "account": {"type": "string", "description": "Account name, e.g. mindglitch.fyi."},
                "niche": {"type": "string", "description": "idea_generate: the niche or account."},
                "pillars": {"type": "array", "items": {"type": "string"}},
                "text": {"type": "string", "description": "The idea, or the pillar to remove."},
                "ideas": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "id": {"type": "integer", "description": "The idea number."},
                "status": {"type": "string", "enum": store.STATUSES},
                "query": {"type": "string"},
                "tag": {"type": "string"},
                "count": {"type": "integer", "description": "idea_generate: how many. Default 10."},
                "winner": {"type": "boolean", "description": "winner_mark: false to undo."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"creator_ideas"}


def run_tool(name: str, args: dict, settings: Settings, http=None, now=None):
    when = store.now(now)
    action = args.get("action")
    plain = {"pillar_add": pillar_add, "pillar_list": pillar_list, "pillar_remove": pillar_remove,
             "idea_list": idea_list, "idea_search": idea_search, "idea_status": idea_status,
             "idea_remove": idea_remove, "winner_mark": winner_mark, "idea_generate": idea_generate, "board": board}
    if action in plain:
        return plain[action](settings, args)
    if action == "idea_add":
        return idea_add(settings, args, when)
    if action == "idea_save":
        return idea_save(settings, args, when)
    raise ValueError("I can't do that one.")
