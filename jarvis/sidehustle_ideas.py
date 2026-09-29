"""Side-hustle idea explorer: about 40 common UK-friendly hustles with typical start cost, time to first pound, skills and
risks, matched to your skills, hours and budget, compared side by side and kept on a shortlist.

Ideas pop up as "sidehustle-ideas", comparisons as "sidehustle-compare" and a single idea as "sidehustle-calc"
(frontend/popup-sidehustle.js). The list is general information written by me, not live data, and never a promise of
income. Your profile and shortlist are saved in sidehustle-profile.json.
"""

import random

import screen
import sidehustle_data as data
import sidehustle_store as st
from config import Settings

NAMES = {"sidehustle_ideas"}
ACTIONS = ["list", "match", "detail", "compare", "save_profile", "profile", "shortlist_add", "shortlist", "shortlist_remove",
           "surprise", "quick_wins", "categories"]
MAX_COMPARE = 4


def _cost(i: dict) -> str:
    lo, hi = i["cost_low"], i["cost_high"]
    return "free" if hi == 0 else (f"about £{hi}" if lo == hi else f"£{lo} to £{hi}")


def _first(i: dict) -> str:
    d = i["first_pound_days"]
    return f"about {d} days" if d < 14 else f"about {round(d / 7)} weeks"


def _row(i: dict, fit: str = "") -> dict:
    return {"name": i["name"], "cost": _cost(i), "first": _first(i), "hours": f"{i['hours_min']}+ hours a week",
            "skills": ", ".join(i["skills"]) or "none needed", "risk": i["risk"], "fit": fit,
            "say": f"Tell me about the {i['name']} side hustle."}


def _shown(text: str, heading: str, items: list[dict], note: str = "", buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card(st.IDEAS, heading, "", buttons=buttons, data={
        "heading": heading, "ideas": items, "note": note or st.HONEST + " Costs and times are rough typical ranges."}))


def _profile(settings: Settings, args: dict) -> dict:
    prof = st.profile(settings)
    skills = data.skills_in(args["skills"]) if args.get("skills") else set(prof.get("skills", []))
    hours = args.get("hours_per_week") if args.get("hours_per_week") is not None else prof.get("hours")
    budget = args.get("budget") if args.get("budget") is not None else prof.get("budget")
    return {"skills": sorted(skills), "hours": float(hours) if hours is not None else None,
            "budget": float(budget) if budget is not None else None}


def _score(i: dict, p: dict) -> tuple[int, str] | None:
    if p["budget"] is not None and i["cost_low"] > p["budget"]:
        return None
    if p["hours"] is not None and i["hours_min"] > p["hours"] + 2:
        return None
    hits = [s for s in i["skills"] if s in p["skills"]]
    score = len(hits) * 3 + (1 if not i["skills"] else 0)
    if p["budget"] is not None and i["cost_high"] <= p["budget"]:
        score += 1
    if p["hours"] is not None and i["hours_min"] <= p["hours"]:
        score += 1
    bits = [f"uses your {', '.join(hits)}"] if hits else ["no matching skill listed"]
    if p["budget"] is not None:
        bits.append("fits your budget" if i["cost_high"] <= p["budget"] else "top end may be over budget")
    return score, "; ".join(bits)


def list_ideas(settings: Settings, args: dict) -> screen.Shown:
    rows = data.all_ideas()
    if args.get("category"):
        cat = st.clean(args["category"]).lower()
        rows = [i for i in rows if i["category"] == cat]
        if not rows:
            raise ValueError("The groups are " + ", ".join(data.CATEGORIES) + ".")
    if args.get("max_cost") is not None:
        rows = [i for i in rows if i["cost_low"] <= float(args["max_cost"])]
    if not rows:
        raise ValueError("Nothing on my list fits that. Try a higher budget.")
    return _shown(f"Here are {len(rows)} side hustle ideas. {st.HONEST}", "Side hustle ideas", [_row(i) for i in rows[:40]],
                  buttons=[{"label": "Match to me", "say": "Match side hustles to my skills, hours and budget."}])


def match(settings: Settings, args: dict) -> screen.Shown:
    p = _profile(settings, args)
    if not (p["skills"] or p["hours"] is not None or p["budget"] is not None):
        raise ValueError("Tell me your skills, hours a week and budget first, for example: I can drive and cook, 5 hours a week, £100.")
    scored = [(s, i) for i in data.all_ideas() if (s := _score(i, p))]
    if not scored:
        raise ValueError("Nothing on my list fits those limits. Try more hours or a bigger budget.")
    scored.sort(key=lambda t: (-t[0][0], t[1]["cost_low"]))
    top = scored[:8]
    return _shown(f"I found {len(scored)} that could fit you; the best is {top[0][1]['name']}. {st.HONEST}", "Matched to you",
                  [_row(i, s[1]) for s, i in top],
                  f"Matched on skills: {', '.join(p['skills']) or 'none given'}; hours: {p['hours'] if p['hours'] is not None else 'any'}; "
                  f"budget: {st.gbp(p['budget']) if p['budget'] is not None else 'any'}. " + st.HONEST)


def detail(settings: Settings, args: dict) -> screen.Shown:
    i = data.idea(st.need(args.get("name"), "side hustle"))
    if not i:
        raise ValueError("I don't have that one on my list. Ask me to list the ideas.")
    rows = [("Start cost", _cost(i)), ("Time to first pound", _first(i) + " (typical, varies a lot)"),
            ("Hours a week", f"{i['hours_min']}+ to make it worthwhile"), ("Skills", ", ".join(i["skills"]) or "none needed"),
            ("Main risk", i["risk"]), ("UK note", i["uk_note"])]
    return st.calc(f"{i['name']}: starts at {_cost(i)}, first pound in {_first(i)}. {st.HONEST}", i["name"], i["name"],
                   f"{i['category']} side hustle", rows, [st.HONEST, st.TAX_NOTE], buttons=[
                       {"label": "Start it", "say": f"Start the {i['name']} side hustle with a 30 day plan."},
                       {"label": "Shortlist", "say": f"Add {i['name']} to my side hustle shortlist."},
                       {"label": "Break-even", "say": f"Work out break-even for {i['name']}."}])


def compare(settings: Settings, args: dict) -> screen.Shown:
    names = args.get("names") or ([args["name"]] if args.get("name") else [])
    if not names:
        names = st.profile(settings).get("shortlist", [])
    picks = []
    for n in names:
        i = data.idea(n)
        if not i:
            raise ValueError(f"I don't have {st.clean(n)} on my list.")
        if i not in picks:
            picks.append(i)
    if len(picks) < 2:
        raise ValueError("Give me two to four side hustles to compare.")
    picks = picks[:MAX_COMPARE]
    labels = [("Start cost", _cost), ("First pound", _first), ("Hours a week", lambda i: f"{i['hours_min']}+"),
              ("Skills", lambda i: ", ".join(i["skills"]) or "none"), ("Main risk", lambda i: i["risk"])]
    rows = [[label] + [fn(i) for i in picks] for label, fn in labels]
    return screen.Shown(f"Comparing {' and '.join(i['name'] for i in picks)}. {st.HONEST}", screen.card(
        st.COMPARE, "Compare side hustles", "", data={"names": [i["name"] for i in picks], "rows": rows,
                                                      "note": st.HONEST + " Typical ranges only."}))


def save_profile(settings: Settings, args: dict) -> str:
    prof = st.profile(settings)
    if args.get("skills"):
        prof["skills"] = sorted(data.skills_in(args["skills"]))
        if not prof["skills"]:
            raise ValueError("I didn't recognise any skills. Try words like driving, cooking, writing, design or gardening.")
    if args.get("hours_per_week") is not None:
        prof["hours"] = st.number(args["hours_per_week"], "hours a week", top=100)
    if args.get("budget") is not None:
        prof["budget"] = st.number(args["budget"], "budget", allow_zero=True)
    st.save(settings, st.PROFILE, prof)
    return "Saved: " + _profile_line(prof)


def _profile_line(prof: dict) -> str:
    return (f"skills {', '.join(prof.get('skills', [])) or 'none yet'}; "
            f"{prof['hours'] if prof.get('hours') is not None else 'no'} hours a week; "
            f"budget {st.gbp(prof['budget']) if prof.get('budget') is not None else 'not set'}.")


def show_profile(settings: Settings) -> screen.Shown:
    prof = st.profile(settings)
    if not prof:
        raise ValueError("I don't have your skills, hours or budget yet.")
    return st.calc("Your side hustle profile: " + _profile_line(prof), "Your side hustle profile",
                   f"{prof.get('hours', '?')} hours a week", "what I match ideas against",
                   [("Skills", ", ".join(prof.get("skills", [])) or "none yet"),
                    ("Budget", st.gbp(prof["budget"]) if prof.get("budget") is not None else "not set"),
                    ("Shortlist", ", ".join(prof.get("shortlist", [])) or "empty")],
                   buttons=[{"label": "Match ideas", "say": "Match side hustles to my profile."}])


def shortlist_add(settings: Settings, args: dict) -> screen.Shown:
    i = data.idea(st.need(args.get("name"), "side hustle"))
    if not i:
        raise ValueError("I don't have that one on my list.")
    prof = st.profile(settings)
    short = prof.setdefault("shortlist", [])
    if i["name"] not in short:
        if len(short) >= 12:
            raise ValueError("Your shortlist is full; remove one first.")
        short.append(i["name"])
        st.save(settings, st.PROFILE, prof)
    return _shortlist(short, f"Added {i['name']} to your shortlist.")


def _shortlist(short: list, prefix: str = "") -> screen.Shown:
    if not short:
        raise ValueError("Your side hustle shortlist is empty.")
    items = [{"label": n, "say": f"Tell me about the {n} side hustle."} for n in short]
    return screen.Shown(f"{prefix} {len(short)} on your shortlist.".strip(), screen.card(
        "list", "Side hustle shortlist", "sidehustle-shortlist", items=items,
        buttons=[{"label": "Compare them", "say": "Compare my shortlisted side hustles."}]))


def shortlist(settings: Settings) -> screen.Shown:
    return _shortlist(st.profile(settings).get("shortlist", []))


def shortlist_remove(settings: Settings, args: dict) -> str:
    prof = st.profile(settings)
    key = st.find(prof.get("shortlist", []), args.get("name", ""))
    if not key:
        raise ValueError("That isn't on your shortlist.")
    prof["shortlist"].remove(key)
    st.save(settings, st.PROFILE, prof)
    return f"Took {key} off your shortlist."


def surprise(settings: Settings, args: dict) -> screen.Shown:
    p = _profile(settings, args)
    pool = [i for i in data.all_ideas() if _score(i, p)] or data.all_ideas()
    i = random.choice(pool)
    return _shown(f"How about {i['name']}? {st.HONEST}", "A side hustle to think about", [_row(i)],
                  buttons=[{"label": "Another", "say": "Surprise me with another side hustle idea."}])


def quick_wins(settings: Settings, args: dict) -> screen.Shown:
    rows = sorted(data.all_ideas(), key=lambda i: (i["first_pound_days"], i["cost_high"]))[:8]
    rows = [i for i in rows if i["cost_high"] <= 100] or rows
    return _shown("These are the quickest and cheapest to start. Quick doesn't mean much money. " + st.HONEST,
                  "Quick and cheap to start", [_row(i) for i in rows])


def categories(settings: Settings) -> screen.Shown:
    counts = {c: sum(1 for i in data.all_ideas() if i["category"] == c) for c in data.CATEGORIES}
    items = [{"label": f"{c} ({n} ideas)", "say": f"List {c} side hustles."} for c, n in counts.items()]
    return screen.Shown("The side hustle groups: " + ", ".join(counts) + ".", screen.card(
        "list", "Side hustle groups", "sidehustle-categories", items=items))


def tool_definitions() -> list[dict]:
    return [{
        "name": "sidehustle_ideas",
        "description": "Find a side hustle: about 40 general UK-friendly ideas with typical start cost, time to first pound, skills "
                       "and risks; list or filter by group or cost, match to the user's skills, hours and budget, detail on one, "
                       "compare 2-4 side by side, save skills/hours/budget, shortlist, random idea, quickest to start. General "
                       "information, never promises income.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "A side hustle name like dog walking."},
                "names": {"type": "array", "items": {"type": "string"}, "description": "2-4 side hustles to compare."},
                "category": {"type": "string", "enum": data.CATEGORIES},
                "skills": {"type": "string", "description": "The user's skills in their own words, e.g. driving, cooking, writing."},
                "hours_per_week": {"type": "number"}, "budget": {"type": "number", "description": "Pounds to spend on starting."},
                "max_cost": {"type": "number", "description": "Highest start cost in pounds."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    simple = {"profile": show_profile, "shortlist": shortlist, "categories": categories}
    handlers = {"list": list_ideas, "match": match, "detail": detail, "compare": compare, "save_profile": save_profile,
                "shortlist_add": shortlist_add, "shortlist_remove": shortlist_remove, "surprise": surprise,
                "quick_wins": quick_wins}
    if action in simple:
        return simple[action](settings)
    if action in handlers:
        return handlers[action](settings, args)
    return list_ideas(settings, args)
