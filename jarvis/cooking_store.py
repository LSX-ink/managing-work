"""Shared bits for the cooking abilities: reading saved recipes (the kitchen's Recipes folder), their steps and
quantities, and the cooking-*.json files in the memory folder.
"""

import re

import homekitchen
import homestore as hs
from config import Settings

META = "cooking-recipes.json"
LEFTOVERS = "cooking-leftovers.json"
FRACTIONS = {"½": 1 / 2, "⅓": 1 / 3, "⅔": 2 / 3, "¼": 1 / 4, "¾": 3 / 4, "⅛": 1 / 8, "⅜": 3 / 8, "⅝": 5 / 8,
             "⅞": 7 / 8, "⅕": 1 / 5, "⅖": 2 / 5, "⅗": 3 / 5, "⅘": 4 / 5, "⅙": 1 / 6, "⅚": 5 / 6}
_FRAC = "[" + "".join(FRACTIONS) + "]"
_NUM = rf"\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?(?:\s*{_FRAC})?|{_FRAC}"
UNITS = {
    "g": "g", "gram": "g", "grams": "g", "kg": "kg", "kilo": "kg", "kilos": "kg", "mg": "mg", "ml": "ml",
    "l": "l", "litre": "l", "litres": "l", "liter": "l", "liters": "l", "tsp": "tsp", "teaspoon": "tsp",
    "teaspoons": "tsp", "tbsp": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp", "cup": "cup", "cups": "cup",
    "oz": "oz", "lb": "lb", "lbs": "lb", "pint": "pint", "pints": "pint", "pinch": "pinch", "pinches": "pinch",
    "clove": "clove", "cloves": "clove", "tin": "tin", "tins": "tin", "can": "can", "cans": "can",
    "slice": "slice", "slices": "slice", "handful": "handful", "handfuls": "handful", "bunch": "bunch",
    "bunches": "bunch", "sprig": "sprig", "sprigs": "sprig", "stick": "stick", "sticks": "stick", "pack": "pack",
    "packs": "pack", "piece": "piece", "pieces": "piece",
}
_UNIT = "|".join(sorted(UNITS, key=len, reverse=True))
QTY = re.compile(rf"^\s*(?P<a>{_NUM})(?:\s*(?:-|–|to)\s*(?P<b>{_NUM}))?\s*(?:(?P<u>{_UNIT})\b\.?)?\s*(?P<rest>.*)$",
                 re.I)
METRIC = {"g": ("g", 1), "kg": ("g", 1000), "mg": ("g", 0.001), "ml": ("ml", 1), "l": ("ml", 1000)}
# Words dropped when matching an ingredient line against the pantry.
FILLER = {"of", "a", "an", "the", "fresh", "chopped", "sliced", "diced", "large", "small", "medium", "finely",
          "roughly", "grated", "minced", "crushed", "peeled", "ripe", "tin", "tins", "can", "cans", "and", "or",
          "to", "taste", "for", "serving", "optional", "about", "x", "whole", "dried", "frozen", "cooked", "raw",
          "boneless", "skinless", "free-range", "organic", "plus", "extra", "some", "few", "good", "pinch"}
STAPLES = {"salt", "pepper", "water", "oil", "olive", "vegetable", "black"}
PLURAL = {"cup": "cups", "clove": "cloves", "tin": "tins", "can": "cans", "slice": "slices", "handful": "handfuls",
          "bunch": "bunches", "sprig": "sprigs", "stick": "sticks", "pack": "packs", "piece": "pieces",
          "pint": "pints", "pinch": "pinches"}


def number(text: str) -> float:
    text = text.strip()
    if text in FRACTIONS:
        return FRACTIONS[text]
    if m := re.fullmatch(r"(\d+)\s+(\d+)/(\d+)", text):
        return int(m[1]) + int(m[2]) / max(1, int(m[3]))
    if m := re.fullmatch(r"(\d+)/(\d+)", text):
        return int(m[1]) / max(1, int(m[2]))
    if m := re.fullmatch(rf"(\d+(?:\.\d+)?)\s*({_FRAC})", text):
        return float(m[1]) + FRACTIONS[m[2]]
    return float(text)


def parse(line: str):
    """(low, high or None, unit, the rest) for an ingredient line starting with a quantity, else None."""
    m = QTY.match(line or "")
    if not m:
        return None
    unit = UNITS.get((m["u"] or "").lower(), "")
    return number(m["a"]), number(m["b"]) if m["b"] else None, unit, m["rest"].strip()


def nice(value: float, unit: str = "") -> str:
    """A quantity written the way a cook would: whole grams, kilos over 1000 g, fractions for spoons and counts."""
    if unit in METRIC:
        base, mult = METRIC[unit]
        value *= mult
        if value >= 1000:
            return f"{value / 1000:.2f}".rstrip("0").rstrip(".") + (" kg" if base == "g" else " l")
        step = 5 if value >= 100 else 1 if value >= 10 else 0.5
        return f"{round(value / step) * step:g} {base}"
    whole = int(value)
    part = value - whole
    options = [(0, ""), (1 / 4, "¼"), (1 / 3, "⅓"), (1 / 2, "½"), (2 / 3, "⅔"), (3 / 4, "¾"), (1, "")]
    if not unit and value >= 1:
        options = [(0, ""), (1 / 2, "½"), (1, "")]
    frac, mark = min(options, key=lambda o: abs(o[0] - part))
    if frac == 1:
        whole, mark = whole + 1, ""
    text = f"{whole or ''}{mark}" or ("⅛" if value > 0 else "0")
    if unit in PLURAL and value > 1:
        unit = PLURAL[unit]
    return f"{text} {unit}".strip()


def scale_line(line: str, factor: float) -> str:
    found = parse(line)
    if not found:
        return line
    low, high, unit, rest = found
    amount = nice(low * factor, unit)
    if high is not None:
        top = nice(high * factor, unit)
        first, _, first_unit = amount.partition(" ")
        amount = f"{first if first_unit and top.endswith(' ' + first_unit) else amount}–{top}"
    return f"{amount} {rest}".strip()


def ingredient_name(line: str) -> str:
    found = parse(line)
    rest = found[3] if found else line
    rest = re.sub(r"\([^)]*\)", " ", rest.split(",")[0]).lower()
    words = [w for w in re.findall(r"[a-z][a-z'-]*", rest) if w not in FILLER and w not in UNITS]
    return " ".join(words)


def _singular(word: str) -> str:
    if word.endswith("oes") or word.endswith("ies"):
        return word[:-3] + ("o" if word.endswith("oes") else "y")
    return word[:-1] if word.endswith("s") and not word.endswith("ss") else word


def words(text: str) -> set[str]:
    return {_singular(w) for w in re.findall(r"[a-z][a-z'-]*", text.lower()) if w not in FILLER}


def have(line: str, pantry: list[str]) -> bool:
    """Whether a pantry item covers this ingredient line (staples such as salt and water always count)."""
    name = ingredient_name(line)
    if not name or words(name) <= STAPLES:
        return True
    need = words(name)
    head = _singular(name.split()[-1])
    for item in pantry:
        got = words(item)
        if got and (got <= need or head in got):
            return True
    return False


# Saved recipes (the kitchen's Recipes folder)

def recipe_names(settings: Settings) -> list[str]:
    return list(homekitchen._recipe_files(settings))


def recipe(settings: Settings, name) -> dict:
    path = homekitchen._recipe(settings, name)
    text = path.read_text(encoding="utf-8")
    serves = re.search(r"(?i)\b(?:serves|servings|portions)\s*:?\s*(\d+)", text)
    return {"name": path.stem, "ingredients": homekitchen.recipe_ingredients(text), "steps": steps(text),
            "serves": int(serves[1]) if serves else None}


def steps(text: str) -> list[str]:
    found, inside = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            inside = line.strip("# ").lower() in ("method", "steps", "instructions", "directions")
        elif inside and (m := re.match(r"^\s*(?:\d+[.)]|[-*])\s+(.+)", line)):
            found.append(m[1].strip())
    return found


def minutes(step: str) -> float | None:
    """The first time a step mentions, in minutes (the shorter end of a range, so you check early)."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:(?:-|–|to)\s*\d+(?:\.\d+)?\s*)?(hours?|hrs?|minutes?|mins?)\b", step, re.I)
    if not m:
        return None
    return float(m[1]) * (60 if m[2].lower().startswith("h") else 1)


def meta(settings: Settings) -> dict:
    return hs.load(settings, META, {})


def save_meta(settings: Settings, data: dict) -> None:
    hs.save(settings, META, data)


def pantry(settings: Settings) -> list[str]:
    return [i["name"] for i in homekitchen._pantry(settings)]
