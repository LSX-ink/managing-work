"""Kitchen: this week's meal plan, saved recipes and what's in the pantry or fridge.

Meals and pantry live in meals.json and pantry.json in the memory folder. Recipes are Markdown files in the
Recipes folder there, so they also show in the HUD's folder panel.
"""

from datetime import timedelta
from pathlib import Path

import homestore as hs
import memory
import shopping
from config import Settings

MEALS = "meals.json"
PANTRY = "pantry.json"
MAX_PANTRY = 300
MAX_STEPS = 60
SLOTS = ("breakfast", "lunch", "dinner")


# Meal planner

def meal_set(settings: Settings, day, meal, slot=None) -> str:
    when = hs.parse_day(day)
    slot = slot if slot in SLOTS else "dinner"
    meal = hs.need(meal, "meal")
    plan = hs.load(settings, MEALS, {})
    today = hs.today()
    keep_from = (hs.week_start(today) - timedelta(days=28)).isoformat()
    plan = {d: v for d, v in plan.items() if d >= keep_from and isinstance(v, dict)}
    plan.setdefault(when.isoformat(), {})[slot] = meal
    hs.save(settings, MEALS, plan)
    return f"{meal} for {slot} on {hs.spoken(when)}."


def meal_week(settings: Settings) -> str:
    plan = hs.load(settings, MEALS, {})
    start = hs.week_start(hs.today())
    lines = []
    for i in range(7):
        day = start + timedelta(days=i)
        meals = plan.get(day.isoformat()) or {}
        if meals:
            lines.append(f"- {day.strftime('%A')}: " + ", ".join(f"{s} {meals[s]}" for s in SLOTS if s in meals))
    return "This week's meals:\n" + "\n".join(lines) if lines else "No meals planned this week."


def meal_clear(settings: Settings, confirmed: bool) -> str:
    if not confirmed:
        return "Ask the user to confirm clearing this week's meal plan, then call again with confirmed true."
    start = hs.week_start(hs.today())
    week = {(start + timedelta(days=i)).isoformat() for i in range(7)}
    plan = {d: v for d, v in hs.load(settings, MEALS, {}).items() if d not in week}
    hs.save(settings, MEALS, plan)
    return "This week's meal plan is cleared."


# Recipes

def recipes_folder(settings: Settings) -> Path:
    return memory.root(settings) / "Recipes"


def _recipe_files(settings: Settings) -> dict[str, Path]:
    folder = recipes_folder(settings)
    return {p.stem: p for p in sorted(folder.glob("*.md"))} if folder.is_dir() else {}


def _recipe(settings: Settings, name) -> Path:
    files = _recipe_files(settings)
    key = hs.find(files, hs.need(name, "recipe"))
    if key is None:
        raise ValueError(f"I haven't got a recipe called {hs.clean(name)}.")
    return files[key]


def _list(values, limit: int) -> list[str]:
    return [hs.clean(v, 200) for v in (values or []) if hs.clean(v)][:limit]


def recipe_save(settings: Settings, name, ingredients, steps, confirmed: bool) -> str:
    title = memory.safe_name(hs.need(name, "recipe", 60), "recipe name")
    ingredients, steps = _list(ingredients, MAX_STEPS), _list(steps, MAX_STEPS)
    if not ingredients:
        raise ValueError("What are the ingredients?")
    old = next((p for k, p in _recipe_files(settings).items() if k.lower() == title.lower()), None)
    if old and not confirmed:
        return f"There's already a recipe called {old.stem}. Ask the user before replacing it, then call again with confirmed true."
    if old:
        old.unlink()
    p = recipes_folder(settings) / f"{title}.md"
    body = f"# {title}\n\n## Ingredients\n" + "".join(f"- {i}\n" for i in ingredients)
    if steps:
        body += "\n## Method\n" + "".join(f"{n}. {s}\n" for n, s in enumerate(steps, 1))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return f"Saved the {title} recipe with {hs.plural(len(ingredients), 'ingredient')}."


def recipe_list(settings: Settings) -> str:
    names = list(_recipe_files(settings))
    return f"{hs.plural(len(names), 'recipe')}: " + ", ".join(names) + "." if names else "No recipes saved yet."


def recipe_read(settings: Settings, name) -> str:
    return _recipe(settings, name).read_text(encoding="utf-8")


def recipe_ingredients(text: str) -> list[str]:
    found, inside = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            inside = line.strip("# ").lower() == "ingredients"
        elif inside and line.startswith("- ") and line[2:].strip():
            found.append(line[2:].strip())
    return found


def recipe_to_shopping(settings: Settings, name) -> str:
    p = _recipe(settings, name)
    ingredients = recipe_ingredients(p.read_text(encoding="utf-8"))
    if not ingredients:
        return f"The {p.stem} recipe has no ingredients listed."
    return f"From {p.stem}: " + shopping.add(settings, ingredients)


# Pantry and fridge

def _pantry(settings: Settings) -> list[dict]:
    return [i for i in hs.load(settings, PANTRY, []) if isinstance(i, dict) and i.get("name")]


def pantry_add(settings: Settings, items, use_by=None) -> str:
    names = _list(items, 50)
    if not names:
        raise ValueError("What should I add?")
    date_text = hs.parse_day(use_by).isoformat() if use_by else ""
    found = _pantry(settings)
    for name in names:
        found = [i for i in found if i["name"].lower() != name.lower()]
        found.append({"name": name, "use_by": date_text})
    if len(found) > MAX_PANTRY:
        raise ValueError("The pantry list is full; use some things up first.")
    hs.save(settings, PANTRY, found)
    when = f", use by {hs.spoken(hs.parse_day(date_text))}" if date_text else ""
    return f"Added {', '.join(names)}{when}. {len(found)} things in the pantry."


def pantry_use(settings: Settings, items) -> str:
    words = [w.lower() for w in _list(items, 50)]
    found = _pantry(settings)
    keep = [i for i in found if not any(w in i["name"].lower() for w in words)]
    gone = [i["name"] for i in found if i not in keep]
    hs.save(settings, PANTRY, keep)
    return (f"Used up {', '.join(gone)}." if gone else "None of those were in the pantry.") + f" {len(keep)} left."


def _when(item: dict) -> str:
    return f" (use by {item['use_by']})" if item.get("use_by") else ""


def pantry_list(settings: Settings) -> str:
    found = sorted(_pantry(settings), key=lambda i: (not i.get("use_by"), i.get("use_by") or "", i["name"].lower()))
    return "In the pantry:\n" + "\n".join(f"- {i['name']}{_when(i)}" for i in found) if found else "The pantry list is empty."


def pantry_expiring(settings: Settings, days=None) -> str:
    days = int(hs.number(days if days is not None else 3, "number of days", 0, 60))
    today = hs.today()
    limit = (today + timedelta(days=days)).isoformat()
    soon = sorted((i for i in _pantry(settings) if i.get("use_by") and i["use_by"] <= limit), key=lambda i: i["use_by"])
    if not soon:
        return f"Nothing goes off in the next {hs.plural(days, 'day')}."
    lines = []
    for i in soon:
        left = (hs.parse_day(i["use_by"]) - today).days
        state = "past its date" if left < 0 else "today" if left == 0 else "tomorrow" if left == 1 else f"in {left} days"
        lines.append(f"- {i['name']}: {state}")
    return "Going off soon:\n" + "\n".join(lines)


def tool_definitions() -> list[dict]:
    listed = {"type": "array", "items": {"type": "string"}}
    return [{
        "name": "home_kitchen",
        "description": "Meal plan, recipes and pantry. meal_set (day: weekday, today, tomorrow or YYYY-MM-DD; meal; "
                       "slot, default dinner), meal_week, meal_clear. recipe_save (name, ingredients, steps), "
                       "recipe_list, recipe_read, recipe_to_shopping adds a recipe's ingredients to the shopping "
                       "list. pantry_add (items, optional use_by YYYY-MM-DD), pantry_use, pantry_list, "
                       "pantry_expiring (days, default 3). Set confirmed true only after the user confirms "
                       "clearing the meal plan or replacing a recipe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "meal_set", "meal_week", "meal_clear", "recipe_save", "recipe_list", "recipe_read",
                    "recipe_to_shopping", "pantry_add", "pantry_use", "pantry_list", "pantry_expiring"]},
                "day": {"type": "string"},
                "meal": {"type": "string"},
                "slot": {"type": "string", "enum": list(SLOTS)},
                "name": {"type": "string", "description": "Recipe name."},
                "ingredients": listed,
                "steps": listed,
                "items": {**listed, "description": "Pantry items, e.g. ['milk', 'eggs']."},
                "use_by": {"type": "string"},
                "days": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"home_kitchen"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action, ok = args.get("action"), bool(args.get("confirmed"))
    if action == "meal_set":
        return meal_set(settings, args.get("day"), args.get("meal"), args.get("slot"))
    if action == "meal_clear":
        return meal_clear(settings, ok)
    if action == "recipe_save":
        return recipe_save(settings, args.get("name"), args.get("ingredients"), args.get("steps"), ok)
    if action == "recipe_list":
        return recipe_list(settings)
    if action == "recipe_read":
        return recipe_read(settings, args.get("name"))
    if action == "recipe_to_shopping":
        return recipe_to_shopping(settings, args.get("name"))
    if action == "pantry_add":
        return pantry_add(settings, args.get("items"), args.get("use_by"))
    if action == "pantry_use":
        return pantry_use(settings, args.get("items"))
    if action == "pantry_list":
        return pantry_list(settings)
    if action == "pantry_expiring":
        return pantry_expiring(settings, args.get("days"))
    return meal_week(settings)
