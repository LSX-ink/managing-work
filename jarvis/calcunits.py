"""Unit conversions: length, weight, volume, area, speed, data sizes, time, temperature and cooking.

Imperial volumes are UK measures unless the unit says US. Cups are US cups (236.6 ml). Cooking conversions
between weight and volume use typical densities, so they are good approximations, not lab figures.
"""

import re

from calcmaths import fmt
from config import Settings

# kind -> (factor to the kind's base unit, names). The first name is the one used in replies.
UNITS = {
    "length": [
        (0.001, "mm", "millimetre", "millimeter"), (0.01, "cm", "centimetre", "centimeter"),
        (1, "m", "metre", "meter"), (1000, "km", "kilometre", "kilometer", "k"),
        (0.0254, "inches", "inch", "in", '"'), (0.3048, "feet", "foot", "ft", "'"), (0.9144, "yards", "yard", "yd"),
        (1609.344, "miles", "mile", "mi"), (1852, "nautical miles", "nautical mile", "nmi"),
    ],
    "weight": [
        (1e-6, "mg", "milligram"), (0.001, "g", "gram", "gramme", "gm"), (1, "kg", "kilogram", "kilo"),
        (1000, "tonnes", "tonne", "metric ton", "t"), (0.028349523125, "oz", "ounce"),
        (0.45359237, "lb", "pound", "lbs"), (6.35029318, "stone", "st", "stones"),
        (907.18474, "US tons", "us ton", "short ton"), (1016.0469088, "UK tons", "uk ton", "long ton", "ton"),
    ],
    "volume": [
        (0.001, "ml", "millilitre", "milliliter", "cc"), (0.01, "cl", "centilitre", "centiliter"),
        (0.1, "dl", "decilitre", "deciliter"), (1, "litres", "litre", "liter", "l"),
        (1000, "cubic metres", "cubic metre", "cubic meter", "m3"),
        (0.005, "tsp", "teaspoon"), (0.015, "tbsp", "tablespoon"),
        (0.2365882365, "cups", "cup", "us cup"), (0.25, "metric cups", "metric cup"),
        (0.0284130625, "fl oz", "fluid ounce", "uk fl oz"), (0.0295735295625, "US fl oz", "us fluid ounce"),
        (0.56826125, "pints", "pint", "uk pint", "pt"), (0.473176473, "US pints", "us pint"),
        (4.54609, "gallons", "gallon", "uk gallon", "gal"), (3.785411784, "US gallons", "us gallon"),
    ],
    "area": [
        (1e-6, "sq mm", "square millimetre", "mm2"), (1e-4, "sq cm", "square centimetre", "cm2"),
        (1, "sq m", "square metre", "square meter", "m2"), (1e6, "sq km", "square kilometre", "km2"),
        (1e4, "hectares", "hectare", "ha"), (4046.8564224, "acres", "acre"),
        (0.00064516, "sq in", "square inch", "square inches", "in2"),
        (0.09290304, "sq ft", "square foot", "square feet", "ft2"), (0.83612736, "sq yd", "square yard", "yd2"),
        (2589988.110336, "sq miles", "square mile", "sq mile", "mi2"),
    ],
    "speed": [
        (1, "m/s", "metres per second", "meters per second", "mps"), (1 / 3.6, "km/h", "kph", "kmh",
                                                                       "kilometres per hour", "km per hour"),
        (0.44704, "mph", "miles per hour", "mi/h"), (1852 / 3600, "knots", "knot", "kn", "kt"),
        (0.3048, "ft/s", "feet per second", "fps"),
    ],
    "data": [
        (1 / 8, "bits", "bit"), (1, "bytes", "byte", "b"), (1e3, "KB", "kilobyte", "kb"), (1e6, "MB", "megabyte", "mb"),
        (1e9, "GB", "gigabyte", "gb", "gig"), (1e12, "TB", "terabyte", "tb"), (1e15, "PB", "petabyte", "pb"),
        (1024, "KiB", "kibibyte", "kib"), (1024 ** 2, "MiB", "mebibyte", "mib"), (1024 ** 3, "GiB", "gibibyte", "gib"),
        (1024 ** 4, "TiB", "tebibyte", "tib"), (1e3 / 8, "kilobits", "kilobit", "kbit"),
        (1e6 / 8, "megabits", "megabit", "mbit"), (1e9 / 8, "gigabits", "gigabit", "gbit"),
    ],
    "time": [
        (0.001, "ms", "millisecond", "msec"), (1, "seconds", "second", "sec", "s"), (60, "minutes", "minute", "min"),
        (3600, "hours", "hour", "hr", "h"), (86400, "days", "day", "d"), (604800, "weeks", "week", "wk"),
        (1209600, "fortnights", "fortnight"), (2629746, "months", "month"), (31556952, "years", "year", "yr"),
        (315569520, "decades", "decade"), (3155695200, "centuries", "century"),
    ],
}
TEMPERATURE = {"c": "°C", "celsius": "°C", "centigrade": "°C", "f": "°F", "fahrenheit": "°F", "k": "K", "kelvin": "K"}
# Grams per millilitre, roughly, for spooned and cupped ingredients.
DENSITY = {
    "flour": 0.53, "plain flour": 0.53, "self-raising flour": 0.53, "bread flour": 0.55, "sugar": 0.85,
    "caster sugar": 0.9, "brown sugar": 0.93, "icing sugar": 0.51, "butter": 0.96, "water": 1.0, "milk": 1.03,
    "cream": 1.0, "oil": 0.92, "honey": 1.42, "golden syrup": 1.4, "rice": 0.78, "oats": 0.38, "cocoa": 0.42,
    "salt": 1.2, "yoghurt": 1.03, "yogurt": 1.03, "ground almonds": 0.4,
}
# UK gas mark -> °C for a conventional oven.
GAS_MARKS = {0.25: 110, 0.5: 130, 1: 140, 2: 150, 3: 170, 4: 180, 5: 190, 6: 200, 7: 220, 8: 230, 9: 240}


def _key(unit: str) -> str:
    text = str(unit or "").strip().lower().replace("²", "2").replace("³", "3").replace("°", "")
    text = re.sub(r"\s+", " ", text).replace("square ", "sq ").replace("sq. ", "sq ")
    return re.sub(r"^degrees? ", "", text)


ALIASES = {}
for _kind, _rows in UNITS.items():
    for _factor, *_names in _rows:
        for _name in _names:
            forms = [_key(_name)] + ([_key(_name) + "s"] if len(_name) > 2 else [])
            for _form in forms:
                ALIASES.setdefault(_form, (_kind, _factor, _names[0]))
ALIASES.update({k: ALIASES[v] for k, v in {"kgs": "kg", "hrs": "hr", "yds": "yd", "gms": "gm"}.items()})


def find(unit: str) -> tuple[str, float, str]:
    key = _key(unit)
    for candidate in (key, key.rstrip("s")):
        if candidate in ALIASES:
            return ALIASES[candidate]
    raise ValueError(f"I don't know the unit '{unit}'.")


def label(name: str, value: float) -> str:
    if value != 1 or not name.endswith("s") or "/" in name or len(name) <= 2:
        return name
    return {"inches": "inch", "feet": "foot", "centuries": "century"}.get(name, name[:-1])


def sig(value: float) -> str:
    return fmt(round(value)) if abs(value) >= 1e6 else fmt(float(f"{value:.6g}"))


def temperature(value: float, source: str, target: str) -> str:
    source, target = TEMPERATURE[_key(source)], TEMPERATURE[_key(target)]
    celsius = {"°C": value, "°F": (value - 32) * 5 / 9, "K": value - 273.15}[source]
    if celsius < -273.15:
        raise ValueError("That's colder than absolute zero.")
    out = {"°C": celsius, "°F": celsius * 9 / 5 + 32, "K": celsius + 273.15}[target]
    return f"{fmt(round(value, 2))}{source} is {fmt(round(out, 2))}{target}."


def _gas(unit: str) -> bool:
    return _key(unit).replace("gas", "").strip() in ("mark", "") and "gas" in _key(unit)


def gas_mark(value: float, source: str, target: str) -> str:
    if _gas(source):
        if value not in GAS_MARKS:
            raise ValueError("Gas marks go from a quarter to 9.")
        celsius = GAS_MARKS[value]
        return (f"Gas mark {fmt(value)} is about {celsius}°C ({celsius - 20}°C fan), "
                f"or {round(celsius * 9 / 5 + 32)}°F.")
    source = TEMPERATURE.get(_key(source))
    if not source:
        raise ValueError("Convert gas marks to or from °C or °F.")
    celsius = value if source == "°C" else (value - 32) * 5 / 9 if source == "°F" else value - 273.15
    mark = min(GAS_MARKS, key=lambda m: abs(GAS_MARKS[m] - celsius))
    return f"{fmt(value)}{source} is about gas mark {fmt(mark)}."


def convert(value, source: str, target: str, ingredient: str = "") -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("The value must be a number.") from None
    if abs(value) > 1e15:
        raise ValueError("That number is too big to convert.")
    if _gas(source) or _gas(target):
        return gas_mark(value, source, target)
    if _key(source) in TEMPERATURE and _key(target) in TEMPERATURE:
        return temperature(value, source, target)
    kind_a, factor_a, name_a = find(source)
    kind_b, factor_b, name_b = find(target)
    if kind_a == kind_b:
        out = value * factor_a / factor_b
        note = " (approximate: months and years are averages)" if kind_a == "time" and {name_a, name_b} & {
            "months", "years", "decades", "centuries"} else ""
        return f"{fmt(value)} {label(name_a, value)} is {sig(out)} {label(name_b, round(out, 6))}{note}."
    if {kind_a, kind_b} == {"weight", "volume"}:
        return cooking(value, (kind_a, factor_a, name_a), (kind_b, factor_b, name_b), ingredient)
    raise ValueError(f"I can't turn {name_a} into {name_b}; they measure different things.")


def cooking(value: float, source: tuple, target: tuple, ingredient: str) -> str:
    food = re.sub(r"\s+", " ", str(ingredient or "")).strip().lower()
    density = DENSITY.get(food) or DENSITY.get(food.rstrip("s"))
    if density is None:
        known = ", ".join(sorted(DENSITY))
        raise ValueError(f"To swap weight and volume I need the ingredient. I know: {known}.")
    if source[0] == "weight":
        out = value * source[1] / density / target[1]
    else:
        out = value * source[1] * density / target[1]
    out = round(out, 0 if out >= 100 else 1 if out >= 10 else 2)
    return f"{fmt(value)} {label(source[2], value)} of {food} is about {fmt(out)} {label(target[2], out)}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "convert_units",
        "description": "Exact unit conversion: length, weight, volume, area, speed, data sizes (KB, MB, GiB, "
                       "megabits), time, temperature (C, F, K), and cooking (tsp, tbsp, cups, ml, fl oz, grams, "
                       "ounces, UK gas marks). Weight to volume needs the ingredient (flour, sugar, butter...). "
                       "Imperial means UK unless the unit says US; cups are US cups.",
        "input_schema": {
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "from": {"type": "string", "description": "Unit, e.g. 'miles', 'lb', 'F', 'cups', 'gas mark'."},
                "to": {"type": "string"},
                "ingredient": {"type": "string", "description": "For cooking weight<->volume, e.g. 'flour'."},
            },
            "required": ["value", "from", "to"],
            "additionalProperties": False,
        },
    }]


NAMES = {"convert_units"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    return convert(args.get("value"), args.get("from") or "", args.get("to") or "", args.get("ingredient") or "")
