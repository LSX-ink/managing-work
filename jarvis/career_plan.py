"""Career planning: compare job offers with a weighted score table, networking contacts to follow up, and career
goals with milestones.

Offers pop up as a "career-compare" window (frontend/popup-career.js). Contacts are linked by name only (the
people notebook is separate). Kept in career-offers.json, career-contacts.json and career-goals.json.
"""

from datetime import timedelta

import career_store as cs
import screen
from config import Settings

KIND = "career-compare"
screen.EXTRA_KINDS.add(KIND)
ACTIONS = ["offer_add", "offer_compare", "offer_weights", "offer_remove", "contact_add", "contact_list",
           "contact_done", "goal_add", "milestone_add", "milestone_done", "goal_show"]
CRITERIA = ["pay", "commute", "holiday", "benefits"]
DEFAULT_WEIGHTS = {"pay": 40, "commute": 20, "holiday": 20, "benefits": 20}
CONTACT_GAP_DAYS = 30


def _num(value, what: str) -> float | None:
    text = cs.clean("" if value is None else str(value)).lower().replace("£", "").replace(",", "")
    if not text:
        return None
    try:
        return float(text[:-1]) * 1000 if text.endswith("k") else float(text)
    except ValueError:
        raise ValueError(f"Give the {what} as a number.") from None


def _offers(settings: Settings) -> dict:
    data = cs.load(settings, cs.OFFERS, {})
    return {"weights": {**DEFAULT_WEIGHTS, **{k: v for k, v in data.get("weights", {}).items() if k in CRITERIA}},
            "offers": {k: v for k, v in data.get("offers", {}).items() if isinstance(v, dict)}}


def offer_add(settings: Settings, args: dict) -> screen.Shown | str:
    name = cs.need(args.get("company"), "company")
    data = _offers(settings)
    if len(data["offers"]) >= 10 and name not in data["offers"]:
        raise ValueError("That's plenty of offers; remove one first.")
    o = data["offers"].setdefault(cs.find(data["offers"], name) or name, {})
    for key, what in (("pay", "pay"), ("commute", "commute minutes"), ("holiday", "holiday days")):
        given = _num(args.get(key), what)
        if given is not None:
            o[key] = given
    if args.get("benefits"):
        o["benefits"] = [cs.clean(b, 60) for b in args["benefits"] if cs.clean(b, 60)][:20]
    pension = _num(args.get("pension"), "pension percent")
    if pension is not None:
        o["pension"] = pension
    cs.save(settings, cs.OFFERS, data)
    if len(data["offers"]) < 2:
        return f"Saved the {name} offer. Add another and I'll compare them side by side."
    return offer_compare(settings, {})


def _benefit_points(o: dict) -> float:
    return len(o.get("benefits", [])) + o.get("pension", 0) / 2


def _values(o: dict) -> dict:
    return {"pay": o.get("pay"), "commute": o.get("commute"), "holiday": o.get("holiday"),
            "benefits": _benefit_points(o) if o.get("benefits") or o.get("pension") else None}


def _score(criterion: str, vals: list) -> list[float]:
    known = [v for v in vals if v]
    if not known:
        return [0.0] * len(vals)
    best = min(known) if criterion == "commute" else max(known)
    return [round(10 * (best / v if criterion == "commute" else v / best), 1) if v else 0.0 for v in vals]


def offer_compare(settings: Settings, args: dict) -> screen.Shown:
    data = _offers(settings)
    names = list(data["offers"])
    if args.get("company") and cs.find(names, args["company"]) is None:
        raise ValueError(f"I don't have an offer from {cs.clean(args['company'])}.")
    if len(names) < 2:
        raise ValueError("I need at least two offers to compare. Tell me the pay, commute and holiday for each.")
    if args.get("company"):
        names = [cs.find(names, args["company"])] + [n for n in names if n != cs.find(names, args["company"])][:1]
    names = names[:4]
    values = {n: _values(data["offers"][n]) for n in names}
    weights = data["weights"]
    total = [0.0] * len(names)
    rows = []
    for c in CRITERIA:
        raw = [values[n][c] for n in names]
        scores = _score(c, raw)
        total = [t + s * weights[c] / 100 for t, s in zip(total, scores)]
        rows.append({"criterion": c, "weight": weights[c], "values": [_show(c, v) for v in raw], "scores": scores})
    total = [round(t, 1) for t in total]
    winner = names[total.index(max(total))]
    tie = total.count(max(total)) > 1
    said = "It's a tie on points." if tie else f"{winner} scores highest, {max(total)} out of 10."
    return screen.Shown(said, screen.card(
        KIND, "Job offers compared", "career-compare", data={"offers": names, "rows": rows, "totals": total},
        buttons=[{"label": "Negotiation script", "say": "Give me a salary negotiation script."}]))


def _show(criterion: str, value) -> str:
    if not value:
        return "?"
    return {"pay": f"£{value:,.0f}", "commute": f"{value:.0f} min", "holiday": f"{value:.0f} days"}.get(criterion, f"{value:g} pts")


def offer_weights(settings: Settings, args: dict) -> screen.Shown:
    weights = args.get("weights") or {}
    given = {c: _num(weights.get(c), c) for c in CRITERIA if weights.get(c) not in (None, "")}
    if not given:
        raise ValueError("Give weights for pay, commute, holiday or benefits, e.g. pay 50.")
    if any(v < 0 for v in given.values()):
        raise ValueError("Weights can't be negative.")
    data = _offers(settings)
    data["weights"].update(given)
    tot = sum(data["weights"].values())
    if not tot:
        raise ValueError("At least one weight has to be above zero.")
    data["weights"] = {c: round(w * 100 / tot, 1) for c, w in data["weights"].items()}
    cs.save(settings, cs.OFFERS, data)
    if len(data["offers"]) >= 2:
        return offer_compare(settings, {})
    return screen.Shown("Saved your weights.", screen.card(
        "table", "Offer weights", "career-weights", columns=["Criterion", "Weight %"],
        rows=[[c, f"{w:g}"] for c, w in data["weights"].items()]))


def offer_remove(settings: Settings, args: dict) -> str:
    data = _offers(settings)
    name = cs.find(data["offers"], cs.need(args.get("company"), "company"))
    if name is None:
        raise ValueError("I don't have that offer.")
    if not args.get("confirmed"):
        return f"Shall I remove the {name} offer? It can't be undone."
    del data["offers"][name]
    cs.save(settings, cs.OFFERS, data)
    return f"Removed the {name} offer."


# ---- networking contacts -------------------------------------------------------------------------

def _contacts(settings: Settings) -> dict:
    return {k: v for k, v in cs.load(settings, cs.CONTACTS, {}).items() if isinstance(v, dict)}


def contact_add(settings: Settings, args: dict) -> screen.Shown:
    name = cs.need(args.get("name"), "name", 60)
    found = _contacts(settings)
    key = cs.find(found, name) or name
    c = found.setdefault(key, {})
    for field, limit in (("company", 60), ("text", 300)):
        if cs.clean(args.get(field), limit):
            c["note" if field == "text" else field] = cs.clean(args.get(field), limit)
    day = cs.parse_date(args.get("follow_up"), "follow-up date") or cs.today() + timedelta(days=14)
    c["follow_up"] = day.isoformat()
    cs.save(settings, cs.CONTACTS, found)
    return contact_list(settings, said=f"Saved {key}. I'll remind you to follow up on {cs.short(day)}.")


def contact_list(settings: Settings, said: str = "") -> screen.Shown | str:
    found = _contacts(settings)
    if not found:
        return "No networking contacts saved yet."
    ordered = sorted(found.items(), key=lambda kv: kv[1].get("follow_up", "9999"))
    due = [n for n, c in ordered if c.get("follow_up") and cs.parse_date(c["follow_up"]) <= cs.today()]
    rows = [[n, c.get("company", ""), c.get("follow_up", ""), c.get("note", "")] for n, c in ordered]
    text = said or (f"{len(due)} contacts are due a follow-up, first {due[0]}." if due else f"{len(found)} contacts, none due yet.")
    return screen.Shown(text, screen.card(
        "table", "Networking contacts", "career-contacts", columns=["Name", "Company", "Follow up", "Note"], rows=rows,
        buttons=[{"label": f"Spoke to {n}"[:40], "say": f"I've followed up with {n}, my networking contact."} for n in due[:3]]))


def contact_done(settings: Settings, args: dict) -> screen.Shown:
    found = _contacts(settings)
    name = cs.find(found, cs.need(args.get("name"), "name", 60))
    if name is None:
        raise ValueError("I don't have that networking contact.")
    day = cs.parse_date(args.get("follow_up"), "follow-up date") or cs.today() + timedelta(days=CONTACT_GAP_DAYS)
    found[name]["follow_up"] = day.isoformat()
    found[name]["last_contact"] = cs.today().isoformat()
    cs.save(settings, cs.CONTACTS, found)
    return contact_list(settings, said=f"Noted. I'll nudge you about {name} again on {cs.short(day)}.")


# ---- career goals ---------------------------------------------------------------------------------

def _goals(settings: Settings) -> dict:
    return {k: v for k, v in cs.load(settings, cs.GOALS, {}).items() if isinstance(v, dict)}


def _goal(found: dict, name) -> str:
    key = cs.find(found, name or "") or (list(found)[-1] if found and not name else None)
    if key is None:
        raise ValueError("Which career goal?" if not found or not name else f"I don't have a career goal called {cs.clean(name)}.")
    return key


def goal_add(settings: Settings, args: dict) -> screen.Shown:
    name = cs.need(args.get("goal"), "goal", 100)
    found = _goals(settings)
    if len(found) >= 30 and name not in found:
        raise ValueError("That's plenty of career goals; finish some first.")
    day = cs.parse_date(args.get("date"), "target date")
    g = found.setdefault(cs.find(found, name) or name, {"milestones": []})
    if day:
        g["target"] = day.isoformat()
    cs.save(settings, cs.GOALS, found)
    return _goal_card(cs.find(found, name) or name, g, f"Saved the career goal {name}.")


def milestone_add(settings: Settings, args: dict) -> screen.Shown:
    found = _goals(settings)
    key = _goal(found, args.get("goal"))
    text = cs.need(args.get("text"), "milestone", 120)
    ms = found[key].setdefault("milestones", [])
    if len(ms) >= 30:
        raise ValueError("That goal already has plenty of milestones.")
    ms.append({"text": text, "done": False})
    cs.save(settings, cs.GOALS, found)
    return _goal_card(key, found[key], f"Added the milestone to {key}.")


def milestone_done(settings: Settings, args: dict) -> screen.Shown:
    found = _goals(settings)
    key = _goal(found, args.get("goal"))
    ms = found[key].get("milestones", [])
    hit = cs.find([m["text"] for m in ms], cs.need(args.get("text"), "milestone"))
    if hit is None:
        raise ValueError(f"{key} has no milestone like that.")
    for m in ms:
        if m["text"] == hit:
            m["done"] = True
    cs.save(settings, cs.GOALS, found)
    left = sum(not m["done"] for m in ms)
    return _goal_card(key, found[key], f"Ticked off {hit}." + (f" {left} to go." if left else " Every milestone is done!"))


def goal_show(settings: Settings, args: dict) -> screen.Shown | str:
    found = _goals(settings)
    if not found:
        return "No career goals yet. Tell me one and we can add milestones."
    key = _goal(found, args.get("goal"))
    g = found[key]
    return _goal_card(key, g, f"{key}: {sum(m['done'] for m in g.get('milestones', []))} of {len(g.get('milestones', []))} milestones done.")


def _goal_card(key: str, g: dict, said: str) -> screen.Shown:
    items = [{"label": m["text"], "done": m["done"], "say": f"Tick off the milestone {m['text']} on my career goal {key}"}
             for m in g.get("milestones", [])]
    title = f"{key}" + (f" (by {cs.short(cs.parse_date(g['target']))})" if g.get("target") else "")
    return screen.Shown(said, screen.card(
        "list", title, f"career-goal-{key}", items=items, checks=True,
        buttons=[{"label": "Add milestone", "say": f"Add a milestone to my career goal {key}: "}]))


def tool_definitions() -> list[dict]:
    listed = {"type": "array", "items": {"type": "string"}}
    return [{
        "name": "career_planning",
        "description": "Career planning. Actions: offer_add (save a job offer's pay in pounds a year, commute "
                       "minutes, holiday days, benefits, pension percent; two offers pop up side by side with a "
                       "weighted score); offer_compare; offer_weights (how much pay, commute, holiday, benefits "
                       "matter); offer_remove (set confirmed true only after the user says yes); contact_add (a "
                       "networking contact to follow up, by name), contact_list, contact_done (I followed up); "
                       "goal_add (a career goal with a target date), milestone_add, milestone_done, goal_show.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "company": {"type": "string", "description": "Offer's company."},
                "pay": {"type": "string"}, "commute": {"type": "string", "description": "Minutes each way."},
                "holiday": {"type": "string", "description": "Days a year."},
                "benefits": listed,
                "weights": {"type": "object", "description": "offer_weights: importance of each, e.g. pay 50.",
                            "properties": {c: {"type": "number"} for c in CRITERIA}, "additionalProperties": False},
                "pension": {"type": "string", "description": "Employer pension percent."},
                "name": {"type": "string", "description": "Contact's name."},
                "follow_up": {"type": "string", "description": "YYYY-MM-DD, 'tomorrow' or 'next week'."},
                "goal": {"type": "string"},
                "date": {"type": "string", "description": "Goal target date, YYYY-MM-DD."},
                "text": {"type": "string", "description": "A note about the contact, or a milestone."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"career_planning"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "offer_add":
        return offer_add(settings, args)
    if action == "offer_compare":
        return offer_compare(settings, args)
    if action == "offer_weights":
        return offer_weights(settings, args)
    if action == "offer_remove":
        return offer_remove(settings, args)
    if action == "contact_add":
        return contact_add(settings, args)
    if action == "contact_list":
        return contact_list(settings)
    if action == "contact_done":
        return contact_done(settings, args)
    if action == "goal_add":
        return goal_add(settings, args)
    if action == "milestone_add":
        return milestone_add(settings, args)
    if action == "milestone_done":
        return milestone_done(settings, args)
    if action == "goal_show":
        return goal_show(settings, args)
    raise ValueError(f"Try one of: {', '.join(ACTIONS)}.")
