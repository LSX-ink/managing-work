"""Recipes and drinks from the web in a pop-up: TheMealDB and TheCocktailDB searches with pictures, any recipe web
page (schema.org Recipe data), and buttons to save the recipe or put its ingredients on the shopping list.

A recipe is named by its source: "mealdb:<id>", "cocktaildb:<id>" or an https link to a recipe page.
Saving uses the kitchen's recipe book (homekitchen) and the shopping list (shopping).
"""

import json
import re

import httpx

import homekitchen
import screen
import shopping
import webview_common as web
from config import Settings

screen.EXTRA_KINDS.update({"recipe", "gallery"})

MEALDB = "https://www.themealdb.com/api/json/v1/1"
COCKTAILDB = "https://www.thecocktaildb.com/api/json/v1/1"
DBS = {"mealdb": (MEALDB, "meals", "Meal", "TheMealDB"), "cocktaildb": (COCKTAILDB, "drinks", "Drink", "TheCocktailDB")}
MAX_LINES = 60
ACTIONS = ["meal_search", "cocktail_search", "recipe_show", "recipe_save", "recipe_to_shopping"]


def _steps(text: str) -> list[str]:
    lines = [re.sub(r"^(step\s*\d+[:.)]?|\d+[.)])\s*", "", web.clean(x, 600), flags=re.I)
             for x in re.split(r"\r?\n+", str(text or ""))]
    lines = [x for x in lines if len(x) > 2]
    if len(lines) == 1:
        lines = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", lines[0]) if s]
    return lines[:MAX_LINES]


def _from_db(db: str, row: dict) -> dict:
    _, _, key, site = DBS[db]
    ingredients = []
    for n in range(1, 21):
        what = web.clean(row.get(f"strIngredient{n}"), 80)
        if what:
            ingredients.append(" ".join(x for x in (web.clean(row.get(f"strMeasure{n}"), 40), what) if x))
    about = [web.clean(row.get(k), 40) for k in ("strCategory", "strArea", "strAlcoholic", "strGlass")]
    return {"title": web.clean(row.get(f"str{key}"), 100), "image": web.https(row.get(f"str{key}Thumb")),
            "ingredients": ingredients, "steps": _steps(row.get("strInstructions")),
            "about": " · ".join(a for a in about if a), "site": site, "source": f"{db}:{row.get(f'id{key}')}"}


async def search(http: httpx.AsyncClient, db: str, query: str, alcohol_free: bool = False) -> screen.Shown:
    base, field, key, site = DBS[db]
    if db == "cocktaildb" and alcohol_free and not query:
        body = await web.get_json(http, f"{base}/filter.php", site, {"a": "Non_Alcoholic"})
    else:
        body = await web.get_json(http, f"{base}/search.php", site, {"s": web.need(query, "dish or drink", 80)})
    rows = [r for r in (body.get(field) or []) if isinstance(r, dict)] if isinstance(body, dict) else []
    if alcohol_free:
        rows = [r for r in rows if "strAlcoholic" not in r or "non" in str(r.get("strAlcoholic")).lower()]
    rows = rows[:16]
    what = "mocktails" if alcohol_free else ("drinks" if db == "cocktaildb" else "recipes")
    if not rows:
        raise ValueError(f"{site} has no {what} for {query}." if query else f"{site} has no {what} right now.")
    tiles = [{"title": web.clean(r.get(f"str{key}"), 100),
              "subtitle": " · ".join(x for x in (web.clean(r.get("strCategory"), 40), web.clean(r.get("strArea"), 40),
                                                 web.clean(r.get("strAlcoholic"), 40)) if x),
              "image": web.https(r.get(f"str{key}Thumb")),
              "say": f"Show me the recipe {db}:{r.get(f'id{key}')} on screen."} for r in rows]
    title = f"{what.title()}: {query}" if query else what.title()
    card = screen.card("gallery", title, f"webview-{db}", data={"tiles": tiles}, text="Tap one for the full recipe.")
    return screen.Shown(f"I found {len(tiles)} {what}, with pictures on the screen; the first is {tiles[0]['title']}.", card)


def _find_recipe(node):
    if isinstance(node, list):
        for x in node:
            if found := _find_recipe(x):
                return found
    elif isinstance(node, dict):
        kind = node.get("@type")
        if kind == "Recipe" or (isinstance(kind, list) and "Recipe" in kind):
            return node
        for key in ("@graph", "mainEntity", "itemListElement"):
            if found := _find_recipe(node.get(key)):
                return found
    return None


def _instructions(node) -> list[str]:
    if isinstance(node, str):
        return _steps(node)
    if isinstance(node, list):
        return [s for x in node for s in _instructions(x)][:MAX_LINES]
    if isinstance(node, dict):
        if node.get("itemListElement"):
            return _instructions(node["itemListElement"])
        return [web.clean(node.get("text") or node.get("name"), 600)] if node.get("text") or node.get("name") else []
    return []


def _image(node) -> str:
    if isinstance(node, list):
        return next((u for u in map(_image, node) if u), "")
    if isinstance(node, dict):
        return web.https(node.get("url"))
    return web.https(node)


def parse_recipe_page(markup: str, url: str) -> dict:
    """The schema.org Recipe in a page's JSON-LD blocks, or ValueError."""
    for block in re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', markup):
        try:
            found = _find_recipe(json.loads(block.strip()))
        except ValueError:
            continue
        if found:
            ingredients = [web.clean(i, 150) for i in found.get("recipeIngredient") or found.get("ingredients") or []
                           if isinstance(i, str) and web.clean(i)][:MAX_LINES]
            about = [web.clean(found.get("recipeYield")[0] if isinstance(found.get("recipeYield"), list)
                               else found.get("recipeYield"), 40)]
            total = re.fullmatch(r"P(?:T)?(?:(\d+)H)?(?:(\d+)M)?", str(found.get("totalTime") or ""))
            if total and any(total.groups()):
                h, m = (int(x or 0) for x in total.groups())
                about.append(f"{h} h {m} min" if h else f"{m} min")
            return {"title": web.clean(found.get("name"), 100) or "Recipe", "image": _image(found.get("image")),
                    "ingredients": ingredients, "steps": _instructions(found.get("recipeInstructions")),
                    "about": " · ".join(a for a in about if a), "site": web.clean(url.split("/")[2], 80),
                    "source": url}
    raise ValueError("I couldn't find a recipe on that page.")


async def get_recipe(http: httpx.AsyncClient, source: str) -> dict:
    source = str(source or "").strip()
    m = re.fullmatch(r"(mealdb|cocktaildb):(\d{1,10})", source)
    if m:
        base, field, _, site = DBS[m.group(1)]
        body = await web.get_json(http, f"{base}/lookup.php", site, {"i": m.group(2)})
        rows = (body.get(field) or []) if isinstance(body, dict) else []
        if not rows:
            raise ValueError(f"{site} has no recipe {m.group(2)}.")
        return _from_db(m.group(1), rows[0])
    if not source:
        raise ValueError("Which recipe? Give a recipe link, or search first.")
    r = await web.get_public(http, source, "recipe page")
    return parse_recipe_page(r.text, str(r.url))


def recipe_card(recipe: dict) -> dict:
    source = recipe["source"]
    return screen.card("recipe", recipe["title"], f"webview-recipe-{source}", data={
        k: recipe[k] for k in ("title", "image", "ingredients", "steps", "about", "site")},
        buttons=[{"label": "Save recipe", "say": f"Save the web recipe {source} to my recipes."},
                 {"label": "Add ingredients to shopping list",
                  "say": f"Add the ingredients of the web recipe {source} to my shopping list."}])


async def show(http: httpx.AsyncClient, source: str) -> screen.Shown:
    recipe = await get_recipe(http, source)
    return screen.Shown(f"The {recipe['title']} recipe is on the screen: {len(recipe['ingredients'])} ingredients and "
                        f"{len(recipe['steps'])} steps.", recipe_card(recipe))


async def save(settings: Settings, http: httpx.AsyncClient, source: str, confirmed: bool) -> str:
    recipe = await get_recipe(http, source)
    title = re.sub(r'[<>:"/\\|?*]', "", recipe["title"])[:60]
    return homekitchen.recipe_save(settings, title, recipe["ingredients"], recipe["steps"], confirmed)


async def to_shopping(settings: Settings, http: httpx.AsyncClient, source: str) -> str:
    recipe = await get_recipe(http, source)
    if not recipe["ingredients"]:
        return f"The {recipe['title']} recipe has no ingredients listed."
    return f"From {recipe['title']}: " + shopping.add(settings, recipe["ingredients"])


def tool_definitions() -> list[dict]:
    return [{
        "name": "recipes_and_cocktails",
        "description": "Recipes and drinks from the web in a pop-up on the Alfred screen, with pictures. "
                       "meal_search: find recipes for a dish (TheMealDB); cocktail_search: find cocktails, or "
                       "mocktails with alcohol_free (no query lists them all); recipe_show: the full recipe with an "
                       "ingredients checklist and steps, source 'mealdb:<id>', 'cocktaildb:<id>' or a recipe web "
                       "page link; recipe_save: save it into the user's recipes; recipe_to_shopping: add its "
                       "ingredients to the shopping list. Set confirmed true only after the user agrees to replace "
                       "a saved recipe with the same name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "query": {"type": "string", "description": "Dish or drink name, e.g. 'lasagne' or 'mojito'."},
                "source": {"type": "string", "description": "mealdb:<id>, cocktaildb:<id> or an https recipe link."},
                "alcohol_free": {"type": "boolean"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"recipes_and_cocktails"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    action, query, source = args.get("action"), (args.get("query") or "").strip(), args.get("source") or ""
    if action == "meal_search":
        return await search(http, "mealdb", query)
    if action == "cocktail_search":
        return await search(http, "cocktaildb", query, bool(args.get("alcohol_free")))
    if action == "recipe_show":
        return await show(http, source)
    if action == "recipe_save":
        return await save(settings, http, source, args.get("confirmed") is True)
    if action == "recipe_to_shopping":
        return await to_shopping(settings, http, source)
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
