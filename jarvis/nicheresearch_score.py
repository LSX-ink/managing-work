"""Niche scorer: add niches or business ideas, rate them 1-5 on demand, competition, passion, skill, profit and
evergreen-ness, weight what matters most, then see a ranked table, a radar pop-up, a side-by-side comparison and the weakest spots.

Data is in nicheresearch.json in the memory folder. Ratings are your own opinion; the score is a thinking aid, not a forecast.
"""

import nicheresearch_store as nr
import screen
from config import Settings

NAMES = {"nicheresearch_score"}
FIXES = {
    "demand": "Look for proof people ask for this: questions in groups, books or courses already selling, search suggestions.",
    "competition": "Narrow the niche or find an angle nobody covers: a smaller audience, a style, a level, a place.",
    "passion": "Ask whether you would still enjoy it after 100 pieces of content. If not, pick a closer topic.",
    "skill": "Plan a small learning project, or team up, or start with the part you can already do well.",
    "profit": "Check what people already pay for near this topic, and whether anyone sells something you could sell.",
    "evergreen": "Aim at the lasting problem underneath the trend, so what you make is still useful next year.",
}


def _find(d: dict, ref) -> dict:
    return nr.pick(d["niches"], ref, "name", "niche")


def add_niche(settings: Settings, args: dict):
    d = nr.open_data(settings)
    if len(d["niches"]) >= nr.MAX_ROWS:
        raise ValueError("The niche list is full; remove old ones first.")
    name = nr.need(args.get("name"), "niche name", 60)
    if any(n["name"].lower() == name.lower() for n in d["niches"]):
        raise ValueError(f"You already have a niche called {name}.")
    row = {"id": nr.next_id(d["niches"]), **nr.new_niche(name, nr.clean(args.get("note"), 300))}
    d["niches"].append(row)
    nr.save(settings, nr.FILE, d)
    return f"Added niche {row['id']}, {name}. Say how you rate its demand, competition, passion, skill, profit and evergreen-ness, 1 to 5."


def list_niches(settings: Settings, args: dict):
    d = nr.open_data(settings)
    if not d["niches"]:
        raise ValueError("No niches yet. Say the name of a niche or idea to add one.")
    w = nr.weights(d)
    rows = []
    for n in d["niches"]:
        score = nr.weighted(n, w)
        rows.append((f"{n['id']}. {n['name']}: {'score ' + str(score) if score is not None else 'not rated yet'}", f"Show the niche radar for {n['name']}"))
    return nr.tappable(f"You have {len(rows)} niches.", "My niches", rows)


def rate_niche(settings: Settings, args: dict):
    d = nr.open_data(settings)
    row = _find(d, args.get("niche"))
    given = {k: nr.rating(args[k], k) for k in nr.CRITERIA if args.get(k) not in (None, "")}
    if not given:
        raise ValueError("Give at least one rating from 1 to 5: demand, competition, passion, skill, profit or evergreen.")
    row["ratings"].update(given)
    nr.save(settings, nr.FILE, d)
    score = nr.weighted(row, nr.weights(d))
    if score is None:
        left = [k for k in nr.CRITERIA if k not in row["ratings"]]
        return f"Saved. Still to rate for {row['name']}: {', '.join(left)}."
    return f"{row['name']} scores {score} out of 100: {nr.band(score)}. {nr.HONEST}"


def set_weights(settings: Settings, args: dict):
    d = nr.open_data(settings)
    if args.get("reset") is True:
        d["weights"] = {}
    else:
        given = {k: int(nr.number(args[f"weight_{k}"], f"{k} weight", 0, 10)) for k in nr.CRITERIA if args.get(f"weight_{k}") is not None}
        if not given:
            raise ValueError("Give weights from 0 to 10, for example weight_demand 5.")
        d["weights"].update(given)
    if sum(nr.weights(d).values()) == 0:
        raise ValueError("At least one weight must be above zero.")
    nr.save(settings, nr.FILE, d)
    return "Weights now: " + ", ".join(f"{k} {v}" for k, v in nr.weights(d).items()) + "."


def ranked_table(settings: Settings, args: dict):
    d = nr.open_data(settings)
    w = nr.weights(d)
    rated = sorted(((nr.weighted(n, w), n) for n in d["niches"] if nr.weighted(n, w) is not None), key=lambda p: -p[0])
    if not rated:
        raise ValueError("No niche has all six ratings yet. Rate one first.")
    rows = [[str(i + 1), n["name"], str(score), nr.band(score)] + [str(n["ratings"][k]) for k in nr.CRITERIA] for i, (score, n) in enumerate(rated)]
    return nr.table(f"{rated[0][1]['name']} is top at {rated[0][0]} out of 100. {nr.HONEST}", "Niche ranking",
                    ["#", "Niche", "Score", "Verdict"] + [k.title() for k in nr.CRITERIA], rows)


def radar(settings: Settings, args: dict):
    d = nr.open_data(settings)
    if nr.clean(args.get("niches")):
        chosen = [_find(d, x) for x in nr.items(args["niches"])][:4]
    elif nr.clean(args.get("niche")):
        chosen = [_find(d, args["niche"])]
    else:
        w = nr.weights(d)
        chosen = sorted((n for n in d["niches"] if nr.weighted(n, w) is not None), key=lambda n: -nr.weighted(n, w))[:3]
    chosen = [n for n in chosen if n["ratings"]]
    if not chosen:
        raise ValueError("Nothing to draw yet. Rate a niche first.")
    w = nr.weights(d)
    card = screen.card(nr.RADAR, "Niche radar", "", data={
        "axes": [k.title() for k in nr.CRITERIA],
        "series": [{"name": n["name"], "values": [n["ratings"].get(k, 0) for k in nr.CRITERIA], "score": nr.weighted(n, w)} for n in chosen],
        "note": nr.HONEST})
    return screen.Shown("Here is the radar. The bigger the shape, the stronger the fit.", card)


def compare_niches(settings: Settings, args: dict):
    d = nr.open_data(settings)
    names = nr.items(args.get("niches"))
    if len(names) < 2:
        raise ValueError("Name at least two niches to compare, for example 'baking, chess'.")
    rows_ = [_find(d, x) for x in names][:4]
    w = nr.weights(d)
    head = ["Measure"] + [n["name"] for n in rows_]
    rows = [[k.title()] + [str(n["ratings"].get(k, "-")) for n in rows_] for k in nr.CRITERIA]
    rows.append(["Score / 100"] + [str(nr.weighted(n, w) if nr.weighted(n, w) is not None else "-") for n in rows_])
    for label, key in (("Competitors noted", "competitors"), ("Pain points noted", "pains"), ("Prices seen", "prices"), ("Experiments run", "experiments")):
        rows.append([label] + [str(len(n[key])) for n in rows_])
    scores = [(nr.weighted(n, w), n["name"]) for n in rows_ if nr.weighted(n, w) is not None]
    spoken = f"{max(scores)[1]} leads on score." if scores else "Rate them to see scores."
    return nr.table(f"Comparing {len(rows_)} niches. {spoken}", "Niche comparison", head, rows)


def explain_criteria(settings: Settings, args: dict):
    return nr.sheet("Here is what each rating means.", "How to rate a niche", [
        ("Rate each one from 1 to 5, where 5 is always the good end", [f"{k.title()}: {v}" for k, v in nr.CRITERIA.items()]),
        ("Weights", ["Demand and profit count most by default. Say 'set weight for passion to 5' to change it."])], nr.HONEST)


def weakest_points(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if not row["ratings"]:
        raise ValueError(f"Rate {row['name']} first.")
    w = nr.weights(d)
    low = sorted(row["ratings"].items(), key=lambda p: (p[1], -w[p[0]]))[:3]
    lines = [(f"{k.title()} is {v}. {FIXES[k]}", f"Add a journal lesson about {k} for {row['name']}") for k, v in low]
    return nr.sheet(f"The weakest spot for {row['name']} is {low[0][0]}.", f"Weak spots: {row['name']}", [("Lowest ratings and what to try", lines)], nr.HONEST)


def edit_niche(settings: Settings, args: dict):
    d = nr.open_data(settings)
    row = _find(d, args.get("niche"))
    if args.get("name"):
        row["name"] = nr.need(args["name"], "niche name", 60)
    if args.get("note") is not None:
        row["note"] = nr.clean(args["note"], 300)
    nr.save(settings, nr.FILE, d)
    return f"Updated niche {row['id']}, {row['name']}."


def remove_niche(settings: Settings, args: dict):
    d = nr.open_data(settings)
    row = _find(d, args.get("niche"))
    ask = nr.confirm_first(args, f"the niche {row['name']} and everything saved under it")
    if ask:
        return ask
    d["niches"] = [n for n in d["niches"] if n is not row]
    nr.save(settings, nr.FILE, d)
    return f"Removed {row['name']}."


ACTIONS = {"add_niche": add_niche, "list_niches": list_niches, "rate_niche": rate_niche, "set_weights": set_weights,
           "ranked_table": ranked_table, "radar": radar, "compare_niches": compare_niches, "explain_criteria": explain_criteria,
           "weakest_points": weakest_points, "edit_niche": edit_niche, "remove_niche": remove_niche}


def tool_definitions() -> list[dict]:
    props = {k: {"type": "number", "description": f"Rating 1-5. {v}"} for k, v in nr.CRITERIA.items()}
    props.update({f"weight_{k}": {"type": "number", "description": "Weight 0-10 for set_weights."} for k in nr.CRITERIA})
    return [{
        "name": "nicheresearch_score",
        "description": "Niche scorer for choosing a business or content niche before spending money: add niches, rate demand, competition, "
                       "passion, skill, profit and evergreen 1-5, set weights, ranked table, radar pop-up, compare niches, explain the "
                       "criteria, weakest points. The user's own opinions, not market data. Set confirmed only after the user agrees to remove_niche.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "niche": {"type": "string", "description": "Niche number or name."}, "name": {"type": "string", "description": "New niche name."},
                "niches": {"type": "string", "description": "Comma-separated niche names (compare, radar)."},
                "note": {"type": "string"}, "reset": {"type": "boolean", "description": "set_weights: back to default weights."},
                "confirmed": {"type": "boolean"}, **props,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    return nr.dispatch(ACTIONS, settings, args)
