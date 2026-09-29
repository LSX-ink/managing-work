"""Repurpose part 3: atomising plans (one long idea into ten short pieces), a repurposing checklist per video, a
what-can-I-make-from-this map and a spread-out posting plan.

Plans and ticks are kept in repurpose.json in the memory folder. Planning only: nothing is posted and no video, picture
or voice is made.
"""

from datetime import date, timedelta

import homestore as hs
import repurpose_store as store
import screen
from config import Settings

ACTIONS = ["atomise", "atoms_show", "atom_done", "atoms_remove", "checklist_make", "checklist_show", "checklist_tick",
           "checklist_remove", "template_show", "template_set", "formats_map", "spread_plan"]
ATOMS = ["The biggest myth about {i}", "The number one mistake people make with {i}", "One step to start {i} today",
         "A short story that shows {i}", "One surprising fact about {i} (check it first)", "A question people ask about {i}",
         "Before and after: {i}", "{i} for total beginners in 30 seconds", "Quick recap: {i} in three points",
         "But what about...? Answer the best objection to {i}", "A checklist for {i}", "Your honest opinion on {i}",
         "What I'd do differently with {i}", "{i}: three words people misuse"]
STEPS = ["Cut a vertical version of 30 to 60 seconds", "Make subtitles", "Write a fresh hook for each platform",
         "Write titles and cover text", "Post the YouTube Short", "Post the Instagram Reel", "Make the Pinterest pin text",
         "Write the X thread", "Write the blog post", "Write the newsletter paragraph", "Note each version in the tracker",
         "Set an evergreen re-post reminder"]
MAP = [["Long video", "Shorts, Reels and TikToks from the best 3 moments", "medium"],
       ["Long video", "Blog post from the transcript", "medium"], ["Long video", "Newsletter paragraph with the link", "low"],
       ["Long video", "Quote cards from the strongest sentences", "low"], ["Long video", "X thread of the main points", "low"],
       ["Short video", "Same clip on Shorts and Reels with a new hook", "low"], ["Short video", "Pinterest pin with cover text", "low"],
       ["Short video", "Part 2 answering the top comment", "medium"], ["Short video", "Subtitled version in SRT for other apps", "low"],
       ["Blog post", "Ten short video scripts", "medium"], ["Blog post", "Newsletter issue", "low"],
       ["Blog post", "Pinterest pins, one per section", "medium"], ["Podcast", "Audio clips as quote cards", "low"],
       ["Podcast", "Show notes and chapters", "low"], ["Podcast", "Blog post from the transcript", "medium"]]
SPREAD = [("TikTok", 0), ("YouTube Shorts", 1), ("Instagram Reels", 2), ("Pinterest", 3), ("X", 5), ("Blog", 7),
          ("Newsletter", 7)]


def _need(text, what: str) -> str:
    return hs.need(text, what, 80)


def _key(mapping: dict, name, what: str) -> str:
    key = hs.find(mapping, _need(name, what))
    if key is None:
        raise ValueError(f"I don't have a {what} like that.")
    return key


# ---- Atoms -----------------------------------------------------------------------------------------

def atomise(settings: Settings, args: dict) -> screen.Shown:
    idea = _need(args.get("idea"), "idea")
    count = int(hs.number(args.get("count") or 10, "count", 3, len(ATOMS)))
    saved = store.load(settings)
    key = hs.find(saved["atoms"], idea) or idea
    saved["atoms"][key] = [{"text": t.format(i=idea), "done": False} for t in ATOMS[:count]]
    if len(saved["atoms"]) > 100:
        raise ValueError("That list is full; remove something first.")
    store.save(settings, saved)
    return _atoms_card(key, saved["atoms"][key], f"{count} short pieces from one idea. Tap one to have it scripted.")


def _atoms_card(key: str, rows: list, spoken: str) -> screen.Shown:
    items = [{"label": r["text"], "done": r["done"], "say": f"Write a 30 second script for this short: {r['text']}"}
             for r in rows]
    done = sum(r["done"] for r in rows)
    return screen.Shown(spoken, screen.card("list", f"{key}: {done} of {len(rows)} made", "repurpose-atoms", items=items))


def atoms_show(settings: Settings, args: dict) -> screen.Shown | str:
    atoms = store.load(settings)["atoms"]
    if not args.get("idea"):
        if not atoms:
            return "You haven't atomised an idea yet."
        items = [{"label": f"{k}: {sum(r['done'] for r in v)} of {len(v)} made", "say": f"Show the atoms for {k}."}
                 for k, v in atoms.items()]
        return screen.Shown(f"{len(items)} atomised ideas.", screen.card("list", "Atomised ideas", "repurpose-atomlist", items=items))
    key = _key(atoms, args["idea"], "atomised idea")
    return _atoms_card(key, atoms[key], f"{key}: {sum(r['done'] for r in atoms[key])} of {len(atoms[key])} made.")


def atom_done(settings: Settings, args: dict) -> screen.Shown:
    saved = store.load(settings)
    key = _key(saved["atoms"], args.get("idea"), "atomised idea")
    rows = saved["atoms"][key]
    n = int(hs.number(args.get("number"), "piece number", 1, len(rows)))
    rows[n - 1]["done"] = args.get("done") is not False
    store.save(settings, saved)
    return _atoms_card(key, rows, f"Piece {n} {'made' if rows[n - 1]['done'] else 'not made'}.")


def atoms_remove(settings: Settings, args: dict) -> str:
    saved = store.load(settings)
    key = _key(saved["atoms"], args.get("idea"), "atomised idea")
    if not args.get("confirmed"):
        return store.confirm_needed(f"the atom plan for {key}")
    del saved["atoms"][key]
    store.save(settings, saved)
    return f"Removed the atom plan for {key}."


# ---- Checklists ------------------------------------------------------------------------------------

def _template(saved: dict) -> list[str]:
    return saved["template"] or STEPS


def _list_card(video: str, steps: list) -> screen.Shown:
    done = sum(s["done"] for s in steps)
    items = [{"label": s["step"], "done": s["done"],
              "say": f"Tick step {i} of the repurposing checklist for {video}."} for i, s in enumerate(steps, 1)]
    return screen.Shown(f"{video}: {done} of {len(steps)} repurposing steps done.",
                        screen.card("list", f"Repurposing: {video}", "repurpose-checklist", items=items))


def checklist_make(settings: Settings, args: dict) -> screen.Shown:
    saved = store.load(settings)
    video = store.video(settings, args, saved)
    if len(saved["checklists"]) >= 200 and video not in saved["checklists"]:
        raise ValueError("That list is full; remove something first.")
    saved["checklists"].setdefault(video, [{"step": s, "done": False} for s in _template(saved)])
    store.save(settings, saved)
    return _list_card(video, saved["checklists"][video])


def checklist_show(settings: Settings, args: dict) -> screen.Shown | str:
    lists = store.load(settings)["checklists"]
    if not args.get("video"):
        if not lists:
            return "You haven't started a repurposing checklist yet."
        items = [{"label": f"{k}: {sum(s['done'] for s in v)} of {len(v)} done", "say": f"Show the repurposing checklist for {k}."}
                 for k, v in lists.items()]
        return screen.Shown(f"{len(items)} videos being repurposed.", screen.card("list", "Repurposing checklists", "repurpose-checklists", items=items))
    key = _key(lists, args["video"], "checklist")
    return _list_card(key, lists[key])


def checklist_tick(settings: Settings, args: dict) -> screen.Shown:
    saved = store.load(settings)
    key = _key(saved["checklists"], args.get("video"), "checklist")
    steps = saved["checklists"][key]
    wanted = str(args.get("step") or "").strip()
    if wanted.isdigit() and 1 <= int(wanted) <= len(steps):
        step = steps[int(wanted) - 1]
    else:
        hit = hs.find([s["step"] for s in steps], wanted)
        if hit is None:
            raise ValueError("Which step? Give me its number or a few of its words.")
        step = next(s for s in steps if s["step"] == hit)
    step["done"] = args.get("done") is not False
    store.save(settings, saved)
    return _list_card(key, steps)


def checklist_remove(settings: Settings, args: dict) -> str:
    saved = store.load(settings)
    key = _key(saved["checklists"], args.get("video"), "checklist")
    if not args.get("confirmed"):
        return store.confirm_needed(f"the checklist for {key}")
    del saved["checklists"][key]
    store.save(settings, saved)
    return f"Removed the checklist for {key}."


def template_show(settings: Settings, args: dict) -> screen.Shown:
    steps = _template(store.load(settings))
    return screen.Shown(f"Your repurposing checklist has {len(steps)} steps.",
                        screen.card("list", "Checklist template", "repurpose-template", items=[{"label": s} for s in steps]))


def template_set(settings: Settings, args: dict) -> screen.Shown:
    saved = store.load(settings)
    given = args.get("steps")
    saved["template"] = [hs.clean(s, 100) for s in (given or []) if hs.clean(s)][:30]
    store.save(settings, saved)
    return template_show(settings, args)


# ---- Maps and plans --------------------------------------------------------------------------------

def formats_map(settings: Settings, args: dict) -> screen.Shown:
    kind = hs.clean(args.get("source")).lower()
    rows = [r for r in MAP if not kind or kind in r[0].lower()]
    if not rows:
        raise ValueError("Try long video, short video, blog post or podcast.")
    return screen.Shown(f"{len(rows)} ways to reuse it.",
                        screen.card("table", "What can I make from it?", "repurpose-map", columns=["From", "Make", "Effort"], rows=rows))


def spread_plan(settings: Settings, args: dict, today: date | None = None) -> screen.Shown:
    today = today or hs.today()
    start = hs.parse_day(args.get("date"), today)
    video = _need(args.get("video"), "video")
    rows = [[p, (start + timedelta(days=d)).isoformat(), "planned"] for p, d in SPREAD]
    if args.get("save"):
        saved = store.load(settings)
        for p, day, _ in rows:
            store.put(saved["versions"], {"id": saved["next_id"], "video": video, "platform": p, "format": "",
                                          "date": day, "status": "planned", "url": "", "note": ""})
            saved["next_id"] += 1
        store.save(settings, saved)
    return screen.Shown(f"A week-long plan for {video}, one platform at a time." + (" Saved to your tracker." if args.get("save") else ""),
                        screen.card("table", f"Spread out: {video}", "repurpose-spread", columns=["Where", "Day", "Status"], rows=rows))


# ---- Tool ------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "repurpose_plan",
        "description": "Plan how to reuse content (planning only). action: atomise (idea, count) = one long idea into "
                       "up to 14 short pieces / atoms_show (idea) / atom_done (idea, number, done) / atoms_remove "
                       "(idea, confirmed only after yes); checklist_make (video) = repurposing checklist for a "
                       "video / checklist_show (video) / checklist_tick (video, step number or words, done) / "
                       "checklist_remove (video, confirmed only after yes); template_show / template_set (steps, "
                       "empty list resets); formats_map (source: long video, short video, blog post, podcast); "
                       "spread_plan (video, date, save) = which platform on which day over a week.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "idea": {"type": "string"},
                "video": {"type": "string"},
                "count": {"type": "integer"},
                "number": {"type": "integer"},
                "step": {"type": "string"},
                "steps": {"type": "array", "items": {"type": "string"}},
                "done": {"type": "boolean", "description": "False to untick."},
                "source": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD, today or a weekday."},
                "save": {"type": "boolean", "description": "spread_plan: also add the days to the tracker as planned."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"repurpose_plan"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"atomise": atomise, "atoms_show": atoms_show, "atom_done": atom_done, "atoms_remove": atoms_remove,
             "checklist_make": checklist_make, "checklist_show": checklist_show, "checklist_tick": checklist_tick,
             "checklist_remove": checklist_remove, "template_show": template_show, "template_set": template_set,
             "formats_map": formats_map, "spread_plan": spread_plan}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
