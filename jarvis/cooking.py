"""Hands-free cooking with saved recipes: cook mode one step at a time, scaling servings, what can I make from the
pantry, batch cooking plans, tonight's summary, dietary tags, ratings, and several kitchen timers on screen.

Recipes are the kitchen's Markdown files (homekitchen); tags, ratings and "made on" dates live in
cooking-recipes.json in the memory folder. The kitchen timers run in the page only, apart from Alfred's own timers.
"""

import time
from datetime import timedelta

import cooking_store as cs
import homekitchen
import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.update({"cooking-steps", "cooking-timers", "cooking-batch"})

TAGS = ["vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free"]
ACTIONS = ["cook_mode", "scale", "what_can_i_make", "batch_plan", "tonight", "tag", "filter_tags", "rate",
           "reviews", "not_cooked_lately"]
MAX_TIMERS = 12
MAX_REVIEWS = 50


# Cook mode

def cook_mode(settings: Settings, name, step=None) -> screen.Shown:
    r = cs.recipe(settings, name)
    if not r["steps"]:
        raise ValueError(f"The {r['name']} recipe has no method steps saved.")
    start = int(hs.number(step or 1, "step", 1, len(r["steps"]))) - 1
    steps = [{"text": s, "minutes": cs.minutes(s)} for s in r["steps"]]
    card = screen.card("cooking-steps", f"Cook: {r['name']}", f"cooking-steps-{r['name']}",
                       data={"recipe": r["name"], "steps": steps, "ingredients": r["ingredients"], "start": start})
    first = r["steps"][start]
    return screen.Shown(f"Cook mode for {r['name']}, {hs.plural(len(steps), 'step')}. Step {start + 1}: {first}", card)


# Scaling

def scale(settings: Settings, name, servings_to, servings_from=None) -> screen.Shown:
    r = cs.recipe(settings, name)
    before = servings_from or r["serves"] or cs.meta(settings).get(r["name"], {}).get("serves")
    if not before:
        raise ValueError(f"How many does the {r['name']} recipe serve as written?")
    before = hs.number(before, "number of servings", 0.5, 200)
    after = hs.number(servings_to, "number of servings", 0.5, 200)
    factor = after / before
    rows = [[line, cs.scale_line(line, factor)] for line in r["ingredients"]]
    data = cs.meta(settings)
    data.setdefault(r["name"], {})["serves"] = before
    cs.save_meta(settings, data)
    card = screen.card("table", f"{r['name']}: {before:g} to {after:g} servings", f"cooking-scale-{r['name']}",
                       columns=[f"For {before:g}", f"For {after:g}"], rows=rows,
                       buttons=[{"label": "Cook mode", "say": f"Start cook mode for {r['name']}."}])
    return screen.Shown(f"Scaled {r['name']} from {before:g} to {after:g} servings; it's on the screen.", card)


# What can I make?

def match(r: dict, pantry: list[str]) -> tuple[list[str], list[str]]:
    got = [i for i in r["ingredients"] if cs.have(i, pantry)]
    return got, [i for i in r["ingredients"] if i not in got]


def what_can_i_make(settings: Settings) -> screen.Shown:
    pantry = cs.pantry(settings)
    names = cs.recipe_names(settings)
    if not names:
        raise ValueError("There are no saved recipes yet.")
    if not pantry:
        raise ValueError("The pantry list is empty; tell me what's in the cupboards and fridge first.")
    ranked = []
    for n in names:
        r = cs.recipe(settings, n)
        if r["ingredients"]:
            got, missing = match(r, pantry)
            ranked.append((len(got) / len(r["ingredients"]), -len(missing), n, missing))
    ranked.sort(reverse=True)
    items = [{"label": f"{n}: {round(share * 100)}%" + (f", missing {', '.join(cs.ingredient_name(m) or m for m in missing[:6])}"
                                                         if missing else ", you've got everything"),
              "say": f"Start cook mode for {n}."} for share, _, n, missing in ranked]
    ready = [n for share, _, n, _ in ranked if share == 1]
    say = (f"You can make {', '.join(ready)} with what you've got." if ready
           else f"Closest is {ranked[0][2]}, missing {hs.plural(-ranked[0][1], 'thing')}." if ranked
           else "None of the recipes have ingredients listed.")
    return screen.Shown(say, screen.card("list", "What can I make?", "cooking-what-can-i-make", items=items))


# Batch cooking

def _combine(recipes: list[dict]) -> tuple[list[list[str]], list[str]]:
    totals, loose = {}, []
    for r in recipes:
        for line in r["ingredients"]:
            found = cs.parse(line)
            name = cs.ingredient_name(line)
            if not found or not name or found[1] is not None:
                loose.append(f"{line} ({r['name']})")
                continue
            amount, _, unit, _ = found
            base, mult = cs.METRIC.get(unit, (unit, 1))
            key = (name, base)
            totals[key] = totals.get(key, 0) + amount * mult
    rows = [[name, cs.nice(amount, base)] for (name, base), amount in sorted(totals.items())]
    return rows, loose


def batch_plan(settings: Settings, names) -> screen.Shown:
    picked = [cs.recipe(settings, n) for n in (names or [])[:8]]
    if len(picked) < 2:
        raise ValueError("Which recipes are you batch cooking? Name at least two.")
    rows, loose = _combine(picked)
    rows += [[line, ""] for line in loose]
    timed = sorted(picked, key=lambda r: -sum(cs.minutes(s) or 0 for s in r["steps"]))
    order = []
    for n, r in enumerate(timed, 1):
        total = sum(cs.minutes(s) or 0 for s in r["steps"])
        tip = "start first, longest cook" if n == 1 else "while the others cook" if n < len(timed) else "last, quickest"
        order.append([str(n), r["name"], f"about {total:g} min" if total else "no times given", tip])
    title = "Batch cook: " + ", ".join(r["name"] for r in picked)
    data = {"shopping": {"columns": ["Ingredient", "Total"], "rows": rows},
            "order": {"columns": ["#", "Recipe", "Time", "When"], "rows": order}}
    buttons = [{"label": "Add to shopping", "say": "Put the ingredients of " + " and ".join(
        f"the {r['name']} recipe" for r in picked) + " on my shopping list."}]
    card = screen.card("cooking-batch", title, "cooking-batch", data=data, buttons=buttons)
    return screen.Shown(f"Batch plan for {hs.plural(len(picked), 'recipe')} is on the screen; start with "
                        f"{timed[0]['name']}.", card)


# Tonight

def tonight(settings: Settings) -> screen.Shown:
    plan = hs.load(settings, homekitchen.MEALS, {}).get(hs.today().isoformat()) or {}
    meal = plan.get("dinner") or next(iter(plan.values()), "")
    items, buttons = [], [{"label": "Kitchen timers", "say": "Open my kitchen timers."}]
    for slot in homekitchen.SLOTS:
        if plan.get(slot):
            items.append({"label": f"{slot.title()}: {plan[slot]}"})
    key = hs.find(cs.recipe_names(settings), meal) if meal else None
    say = f"Tonight it's {meal}." if meal else "Nothing's on the meal plan for tonight."
    if key:
        r = cs.recipe(settings, key)
        _, missing = match(r, cs.pantry(settings))
        items.append({"label": f"Recipe: {hs.plural(len(r['steps']), 'step')}, {hs.plural(len(r['ingredients']), 'ingredient')}",
                      "say": f"Start cook mode for {key}."})
        items.append({"label": "Missing: " + (", ".join(cs.ingredient_name(m) or m for m in missing) or "nothing")})
        buttons.insert(0, {"label": "Recipe steps", "say": f"Start cook mode for {key}."})
        if missing:
            buttons.append({"label": "Add missing to shopping", "say": "Add these to my shopping list: " + ", ".join(
                cs.ingredient_name(m) or m for m in missing) + "."})
            say += f" You're missing {hs.plural(len(missing), 'ingredient')}."
    elif meal:
        items.append({"label": "No saved recipe with that name.", "say": f"Find me a recipe for {meal}."})
    for left in _leftovers_today(settings):
        items.append({"label": f"Leftovers to eat today: {left}"})
    if not items:
        items.append({"label": "Plan tonight's dinner", "say": "What can I make with what's in the pantry?"})
    return screen.Shown(say, screen.card("list", "Tonight's cooking", "cooking-tonight", items=items, buttons=buttons))


def _leftovers_today(settings: Settings) -> list[str]:
    today = hs.today().isoformat()
    return [i["what"] for i in hs.load(settings, cs.LEFTOVERS, []) if isinstance(i, dict)
            and i.get("what") and i.get("eat_by", "9999") <= today]


# Tags, ratings and "made on" dates

def tag(settings: Settings, name, tags, remove: bool = False) -> str:
    key = cs.recipe(settings, name)["name"]
    wanted = [t for t in (tags or []) if t in TAGS]
    if not wanted:
        raise ValueError("Which tags? " + ", ".join(TAGS) + ".")
    data = cs.meta(settings)
    entry = data.setdefault(key, {})
    have = set(entry.get("tags") or [])
    have = have - set(wanted) if remove else have | set(wanted)
    entry["tags"] = [t for t in TAGS if t in have]
    cs.save_meta(settings, data)
    return f"{key} is tagged " + (", ".join(entry["tags"]) or "with nothing") + "."


def filter_tags(settings: Settings, tags) -> screen.Shown:
    wanted = [t for t in (tags or []) if t in TAGS]
    data = cs.meta(settings)
    names = [n for n in cs.recipe_names(settings) if set(wanted) <= set(data.get(n, {}).get("tags") or [])]
    label = " and ".join(wanted) or "any"
    items = [{"label": f"{n} ({', '.join(data.get(n, {}).get('tags') or []) or 'untagged'})",
              "say": f"Start cook mode for {n}."} for n in names]
    say = f"{hs.plural(len(names), 'recipe')} {label}: " + ", ".join(names) + "." if names else f"No {label} recipes saved."
    return screen.Shown(say, screen.card("list", f"Recipes: {label}", "cooking-tags", items=items))


def rate(settings: Settings, name, stars=None, note=None, made_on=None) -> str:
    key = cs.recipe(settings, name)["name"]
    day = hs.parse_day(made_on).isoformat()
    data = cs.meta(settings)
    entry = data.setdefault(key, {})
    review = {"date": day, "note": hs.clean(note, 300)}
    if stars is not None:
        review["stars"] = int(hs.number(stars, "star rating", 1, 5))
    entry["reviews"] = ((entry.get("reviews") or []) + [review])[-MAX_REVIEWS:]
    cs.save_meta(settings, data)
    rated = f", {hs.plural(review['stars'], 'star')}" if "stars" in review else ""
    return f"Noted: made {key} on {hs.spoken(hs.parse_day(day))}{rated}."


def _stats(entry: dict) -> tuple[float | None, int, str, str]:
    reviews = entry.get("reviews") or []
    stars = [r["stars"] for r in reviews if r.get("stars")]
    last = max((r["date"] for r in reviews), default="")
    note = next((r["note"] for r in reversed(reviews) if r.get("note")), "")
    return (sum(stars) / len(stars) if stars else None), len(reviews), last, note


def reviews(settings: Settings, name=None) -> screen.Shown:
    data = cs.meta(settings)
    names = [cs.recipe(settings, name)["name"]] if name else cs.recipe_names(settings)
    stats = sorted(((n, *_stats(data.get(n, {}))) for n in names), key=lambda s: -(s[1] or 0))
    rows = [[n, "★" * round(avg) + f" {avg:.1f}" if avg else "not rated", str(made), last or "never", note]
            for n, avg, made, last, note in stats]
    if name:
        entry = data.get(names[0], {})
        rows = [[names[0], "★" * r["stars"] if r.get("stars") else "", "", r["date"], r.get("note", "")]
                for r in reversed(entry.get("reviews") or [])] or rows
    card = screen.card("table", f"Reviews: {names[0]}" if name else "Recipe ratings", "cooking-reviews",
                       columns=["Recipe", "Stars", "Times made", "Last made", "Note"], rows=rows)
    return screen.Shown(f"Ratings for {hs.plural(len(names), 'recipe')} are on the screen.", card)


def not_cooked_lately(settings: Settings, days=None) -> screen.Shown:
    days = int(hs.number(days if days is not None else 30, "number of days", 1, 3650))
    cutoff = (hs.today() - timedelta(days=days)).isoformat()
    data = cs.meta(settings)
    found = []
    for n in cs.recipe_names(settings):
        avg, _, last, _ = _stats(data.get(n, {}))
        if last < cutoff:
            found.append((last, n, avg))
    found.sort()
    items = [{"label": f"{n}: " + (f"last made {last}" if last else "never made") + (f", {avg:.1f} stars" if avg else ""),
              "say": f"Start cook mode for {n}."} for last, n, avg in found]
    say = (f"Not cooked in {hs.plural(days, 'day')}: " + ", ".join(n for _, n, _ in found[:6]) + "."
           if found else f"You've cooked everything in the last {hs.plural(days, 'day')}.")
    return screen.Shown(say, screen.card("list", "Not cooked in a while", "cooking-not-lately", items=items))


# Kitchen timers (in the page)

def kitchen_timers(timers) -> screen.Shown:
    wanted = []
    for n, t in enumerate((timers or [])[:MAX_TIMERS]):
        name = hs.clean(t.get("name"), 30) or f"Timer {n + 1}"
        mins = hs.number(t.get("minutes"), "number of minutes", 0.1, 24 * 60)
        wanted.append({"name": name, "seconds": round(mins * 60), "key": f"{time.time_ns()}-{n}"})
    card = screen.card("cooking-timers", "Kitchen timers", "cooking-timers", data={"timers": wanted})
    if not wanted:
        return screen.Shown("Kitchen timers are on the screen; add one there.", card)
    return screen.Shown("Started " + ", ".join(f"{t['name']} for {_mins(t['seconds'])}" for t in wanted) + ".", card)


def _mins(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return hs.plural(m, "minute") + (f" {s} seconds" if s else "") if m else f"{s} seconds"


def tool_definitions() -> list[dict]:
    listed = {"type": "array", "items": {"type": "string"}}
    return [{
        "name": "cooking_recipes",
        "description": "Cooking with saved recipes, in pop-ups. cook_mode (name, optional step): hands-free cook mode, "
                       "one step at a time in big text with next/back and timers. scale (name, servings_to, "
                       "servings_from if the recipe doesn't say): scale ingredient quantities for more or fewer "
                       "people. what_can_i_make: saved recipes ranked by what's in the pantry, with missing items. "
                       "batch_plan (names): batch cooking, combined shopping amounts and cooking order. tonight: "
                       "tonight's meal plan, steps, timers, missing ingredients. tag (name, tags, remove) and "
                       "filter_tags (tags): dietary tags like vegetarian, vegan, gluten-free. rate (name, stars 1-5, "
                       "note, made_on YYYY-MM-DD/today) logs cooking it; reviews (optional name); not_cooked_lately "
                       "(days, default 30): what haven't I cooked in a while.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "Saved recipe name."},
                "names": {**listed, "description": "batch_plan: recipe names."},
                "step": {"type": "integer"},
                "servings_to": {"type": "number"},
                "servings_from": {"type": "number"},
                "tags": {"type": "array", "items": {"type": "string", "enum": TAGS}},
                "remove": {"type": "boolean"},
                "stars": {"type": "integer"},
                "note": {"type": "string"},
                "made_on": {"type": "string"},
                "days": {"type": "integer"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }, {
        "name": "cooking_timers",
        "description": "Several named kitchen timers side by side in a pop-up (e.g. pasta 10 minutes, sauce 25), "
                       "with add, pause and cancel on screen and a chime when each ends. Use for more than one "
                       "cooking timer at once or 'open my kitchen timers'; no timers just opens the window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timers": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "minutes": {"type": "number"}},
                    "required": ["minutes"], "additionalProperties": False}},
            },
            "additionalProperties": False,
        },
    }]


NAMES = {"cooking_recipes", "cooking_timers"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    if name == "cooking_timers":
        return kitchen_timers(args.get("timers"))
    action, recipe_name = args.get("action"), args.get("name")
    if action == "cook_mode":
        return cook_mode(settings, recipe_name, args.get("step"))
    if action == "scale":
        return scale(settings, recipe_name, args.get("servings_to"), args.get("servings_from"))
    if action == "what_can_i_make":
        return what_can_i_make(settings)
    if action == "batch_plan":
        return batch_plan(settings, args.get("names"))
    if action == "tag":
        return tag(settings, recipe_name, args.get("tags"), bool(args.get("remove")))
    if action == "filter_tags":
        return filter_tags(settings, args.get("tags"))
    if action == "rate":
        return rate(settings, recipe_name, args.get("stars"), args.get("note"), args.get("made_on"))
    if action == "reviews":
        return reviews(settings, recipe_name)
    if action == "not_cooked_lately":
        return not_cooked_lately(settings, args.get("days"))
    return tonight(settings)
