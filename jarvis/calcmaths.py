"""Exact maths: a safe calculator (parsed, never eval'd), BMI with the NHS category, and Roman numerals."""

import ast
import math
import operator
import re

from config import Settings

MAX_CHARS = 300
MAX_NODES = 200
MAX_MAGNITUDE = 1e100
MAX_POWER_DIGITS = 100

BINARY = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: pow,
}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
CONSTANTS = {"pi": math.pi, "e": math.e}


def _log(x, base=None):
    return math.log(x) if base is None else math.log(x, base)


def _factorial(n):
    if n != int(n) or not 0 <= n <= 69:
        raise ValueError("Factorial needs a whole number from 0 to 69.")
    return math.factorial(int(n))


def _round(x, digits=0):
    if digits != int(digits) or not -10 <= digits <= 15:
        raise ValueError("Round to between -10 and 15 decimal places.")
    return round(x, int(digits))


FUNCTIONS = {
    "sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x), "abs": abs,
    "round": _round, "floor": math.floor, "ceil": math.ceil, "log": _log, "ln": math.log,
    "log10": math.log10, "log2": math.log2, "exp": math.exp, "factorial": _factorial,
    "sin": lambda d: math.sin(math.radians(d)), "cos": lambda d: math.cos(math.radians(d)),
    "tan": lambda d: math.tan(math.radians(d)), "min": min, "max": max,
}


def _clean(expression: str) -> str:
    text = str(expression or "").strip()
    if not text:
        raise ValueError("Give me something to work out.")
    if len(text) > MAX_CHARS:
        raise ValueError("That sum is too long for me.")
    text = text.replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**")
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%(?!\s*[\d(.])", r"(\1/100)", text)
    return text


def _check(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("That doesn't give a real number.")
    if isinstance(value, complex):
        raise ValueError("That doesn't give a real number.")
    if abs(value) > MAX_MAGNITUDE:
        raise ValueError("That number is too big to be useful.")
    return value


def _power(base, exponent):
    if base and exponent * math.log10(abs(base)) > MAX_POWER_DIGITS:
        raise ValueError("That number is too big to be useful.")
    try:
        return pow(base, exponent)
    except ZeroDivisionError:
        raise ValueError("You can't divide by zero.") from None


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Name) and node.id.lower() in CONSTANTS:
        return CONSTANTS[node.id.lower()]
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow):
            return _check(_power(left, right))
        try:
            return _check(BINARY[type(node.op)](left, right))
        except ZeroDivisionError:
            raise ValueError("You can't divide by zero.") from None
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id.lower() in FUNCTIONS
            and not node.keywords and 1 <= len(node.args) <= 10):
        values = [_eval(a) for a in node.args]
        try:
            return _check(FUNCTIONS[node.func.id.lower()](*values))
        except (TypeError, OverflowError):
            raise ValueError(f"{node.func.id} can't take those numbers.") from None
        except ValueError as exc:
            if "domain" in str(exc):
                raise ValueError(f"{node.func.id} can't take that number.") from None
            raise
    raise ValueError("I can only do numbers, + - * / ** %, brackets and functions like sqrt and round.")


def fmt(value) -> str:
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.10g}"


def calculate(expression: str) -> str:
    text = _clean(expression)
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        raise ValueError("I couldn't read that sum.") from None
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise ValueError("That sum is too long for me.")
    try:
        value = _eval(tree)
    except (ValueError, ArithmeticError) as exc:
        raise ValueError(str(exc) if isinstance(exc, ValueError) else "That doesn't give a real number.") from None
    return f"{expression.strip()} = {fmt(value)}"


NHS_BMI = ((18.5, "underweight"), (25, "healthy weight"), (30, "overweight"), (40, "obese"))


def bmi(args: dict) -> str:
    height_cm = float(args.get("height_cm") or 0) or (float(args.get("feet") or 0) * 12
                                                       + float(args.get("inches") or 0)) * 2.54
    weight_kg = float(args.get("weight_kg") or 0) or (float(args.get("stone") or 0) * 14
                                                       + float(args.get("pounds") or 0)) * 0.45359237
    if not 50 <= height_cm <= 260 or not 10 <= weight_kg <= 400:
        raise ValueError("I need a height and weight, e.g. 175 cm and 70 kg, or 5 feet 9 and 11 stone.")
    value = weight_kg / (height_cm / 100) ** 2
    category = next((name for limit, name in NHS_BMI if value < limit), "severely obese")
    return (f"BMI {value:.1f}, which the NHS calls {category} for adults. (Height {height_cm:.0f} cm, "
            f"weight {weight_kg:.1f} kg. BMI is a rough guide; it doesn't suit children, and some ethnic groups "
            f"use lower thresholds.)")


ROMAN = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
         (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))


def to_roman(number: int) -> str:
    if not 1 <= number <= 3999:
        raise ValueError("Roman numerals go from 1 to 3999.")
    out = ""
    for value, letters in ROMAN:
        count, number = divmod(number, value)
        out += letters * count
    return out


def from_roman(text: str) -> int:
    text = text.strip().upper()
    total, i = 0, 0
    for value, letters in ROMAN:
        while text.startswith(letters, i):
            total += value
            i += len(letters)
    if not text or i != len(text) or to_roman(total) != text:
        raise ValueError(f"{text or 'That'} isn't a valid Roman numeral.")
    return total


def roman(value) -> str:
    text = str(value if value is not None else "").strip()
    if re.fullmatch(r"\d+", text):
        return f"{int(text)} in Roman numerals is {to_roman(int(text))}."
    return f"{text.upper()} is {from_roman(text)}."


def tool_definitions() -> list[dict]:
    num = {"type": "number"}
    return [{
        "name": "calculate",
        "description": "Exact maths; use it instead of working sums out yourself. action 'sum' evaluates "
                       "expression (numbers, + - * / ** % brackets, sqrt, cbrt, round(x, places), abs, floor, "
                       "ceil, log, ln, log10, exp, factorial, sin/cos/tan in degrees, min, max, pi). 'bmi' takes "
                       "height_cm and weight_kg, or feet+inches and stone+pounds, and gives the NHS category. "
                       "'roman' converts value either way (number to numerals or numerals to number).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["sum", "bmi", "roman"]},
                "expression": {"type": "string", "description": "e.g. '(12.5 + 3) * 4 / 7'"},
                "height_cm": num, "weight_kg": num, "feet": num, "inches": num, "stone": num, "pounds": num,
                "value": {"type": "string", "description": "For roman: e.g. '1987' or 'MCMLXXXVII'."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"calculate"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action = args.get("action")
    if action == "bmi":
        return bmi(args)
    if action == "roman":
        return roman(args.get("value"))
    return calculate(str(args.get("expression") or ""))
