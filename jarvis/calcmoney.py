"""Everyday money maths: percentages, tips, loans, savings, UK take-home pay, VAT, unit prices and fuel cost.

Take-home pay is an estimate for England in the 2026/27 tax year: income tax, employee Class 1 National
Insurance, an optional workplace pension (taken before tax) and an optional Plan 2 student loan.
"""

import math

import calcunits
from calcmaths import fmt
from config import Settings

SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€"}
LITRES_PER_UK_GALLON = 4.54609

PERSONAL_ALLOWANCE = 12_570
TAPER_START = 100_000
BASIC_BAND = 37_700
ADDITIONAL_FROM = 125_140
NI_PRIMARY = 12_570
NI_UPPER = 50_270
PLAN2_THRESHOLD = 29_385
# Unit prices are quoted per this much of the base unit (kg, litre, metre...).
PER = {"weight": (0.1, "100 g"), "volume": (0.1, "100 ml"), "length": (1, "metre"), "area": (1, "square metre"),
       "items": (1, "item")}


def money(amount: float, settings: Settings) -> str:
    code = (settings.currency or "GBP").upper()
    text = f"{abs(amount):,.2f}"
    sign = "-" if amount < 0 else ""
    return f"{sign}{SYMBOLS[code]}{text}" if code in SYMBOLS else f"{sign}{text} {code}"


def _num(args: dict, key: str, what: str, default=None, low=0.0, high=1e12) -> float:
    value = args.get(key)
    if value is None:
        if default is None:
            raise ValueError(f"I need the {what}.")
        return default
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"The {what} must be a number.") from None
    if not low <= value <= high:
        raise ValueError(f"That {what} doesn't look right.")
    return value


def _pct(n: float) -> str:
    return f"{fmt(round(n, 2))}%"


def percent_of(args, settings) -> str:
    pct, amount = _num(args, "percent", "percentage", low=-1e6), _num(args, "amount", "amount", low=-1e12)
    return f"{_pct(pct)} of {fmt(amount)} is {fmt(round(amount * pct / 100, 4))}."


def percent_is(args, settings) -> str:
    part, whole = _num(args, "amount", "part", low=-1e12), _num(args, "total", "total", low=-1e12)
    if whole == 0:
        raise ValueError("The total can't be zero.")
    return f"{fmt(part)} is {_pct(part / whole * 100)} of {fmt(whole)}."


def percent_change(args, settings) -> str:
    old, new = _num(args, "amount", "starting value", low=-1e12), _num(args, "total", "new value", low=-1e12)
    if old == 0:
        raise ValueError("I can't work out a percentage change from zero.")
    change = (new - old) / abs(old) * 100
    word = "up" if change > 0 else "down" if change < 0 else "unchanged"
    return f"From {fmt(old)} to {fmt(new)} is {word}" + (f" {_pct(abs(change))}." if change else ".")


def tip(args, settings) -> str:
    bill = _num(args, "amount", "bill")
    pct = _num(args, "percent", "tip percentage", default=0.0, high=100)
    people = int(_num(args, "people", "number of people", default=1, low=1, high=100))
    tip_amount = round(bill * pct / 100, 2)
    total = bill + tip_amount
    each = math.ceil(total * 100 / people) / 100
    parts = [f"Tip {money(tip_amount, settings)}, total {money(total, settings)}." if pct else
             f"Total {money(total, settings)}."]
    if people > 1:
        parts.append(f"Split {people} ways that's {money(each, settings)} each"
                     + (" (rounded up to the penny)." if round(each * people, 2) != round(total, 2) else "."))
    return " ".join(parts)


def _monthly_payment(principal: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 100 / 12
    return principal / months if r == 0 else principal * r / (1 - (1 + r) ** -months)


def loan(args, settings) -> str:
    principal = _num(args, "amount", "loan amount", low=1)
    rate = _num(args, "rate", "interest rate", high=100)
    months = round(_num(args, "years", "term in years", low=1 / 12, high=50) * 12)
    pay = _monthly_payment(principal, rate, months)
    total = pay * months
    return (f"Borrowing {money(principal, settings)} at {_pct(rate)} a year over {months} months: "
            f"{money(pay, settings)} a month, {money(total, settings)} in total, of which "
            f"{money(total - principal, settings)} is interest. (Repayment loan, fixed rate, interest monthly.)")


def _grow(start: float, monthly: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 100 / 12
    balance = start
    for _ in range(months):
        balance = balance * (1 + r) + monthly
    return balance


def savings_growth(args, settings) -> str:
    start = _num(args, "amount", "starting amount", default=0.0)
    monthly = _num(args, "monthly", "monthly deposit", default=0.0)
    rate = _num(args, "rate", "interest rate", high=100)
    months = round(_num(args, "years", "number of years", low=1 / 12, high=100) * 12)
    final = _grow(start, monthly, rate, months)
    paid_in = start + monthly * months
    return (f"After {fmt(round(months / 12, 2))} years at {_pct(rate)} a year (compounded monthly) you'd have "
            f"{money(final, settings)}: {money(paid_in, settings)} paid in and "
            f"{money(final - paid_in, settings)} interest.")


def savings_goal(args, settings) -> str:
    goal = _num(args, "total", "goal", low=1)
    start = _num(args, "amount", "starting amount", default=0.0)
    monthly = _num(args, "monthly", "monthly deposit", default=0.0)
    rate = _num(args, "rate", "interest rate", default=0.0, high=100)
    if start >= goal:
        return f"You're already there: {money(start, settings)} is at least {money(goal, settings)}."
    balance, months, r = start, 0, rate / 100 / 12
    while balance < goal:
        months += 1
        balance = balance * (1 + r) + monthly
        if months > 1200:
            raise ValueError("At that rate you'd never get there; try a bigger monthly deposit.")
    years, rest = divmod(months, 12)
    span = " and ".join(p for p in (f"{years} year{'s' * (years != 1)}" if years else "",
                                    f"{rest} month{'s' * (rest != 1)}" if rest else "") if p)
    return (f"Saving {money(monthly, settings)} a month at {_pct(rate)} you'd reach {money(goal, settings)} "
            f"in {span} ({months} months), with {money(balance, settings)} by then.")


def income_tax(income: float) -> float:
    allowance = max(0.0, PERSONAL_ALLOWANCE - max(0.0, income - TAPER_START) / 2)
    taxable = max(0.0, income - allowance)
    basic = min(taxable, BASIC_BAND)
    higher = max(0.0, min(taxable, ADDITIONAL_FROM) - BASIC_BAND)
    additional = max(0.0, taxable - ADDITIONAL_FROM)
    return basic * 0.20 + higher * 0.40 + additional * 0.45


def national_insurance(gross: float) -> float:
    return max(0.0, min(gross, NI_UPPER) - NI_PRIMARY) * 0.08 + max(0.0, gross - NI_UPPER) * 0.02


def take_home(args, settings) -> str:
    gross = _num(args, "amount", "yearly salary", high=100_000_000)
    pension_pct = _num(args, "percent", "pension percentage", default=0.0, high=100)
    pension = gross * pension_pct / 100
    tax = income_tax(gross - pension)
    ni = national_insurance(gross)
    loan_repay = max(0.0, gross - PLAN2_THRESHOLD) * 0.09 if args.get("student_loan") else 0.0
    net = gross - pension - tax - ni - loan_repay
    parts = [f"income tax {money(tax, settings)}", f"National Insurance {money(ni, settings)}"]
    if pension:
        parts.append(f"pension {money(pension, settings)}")
    if args.get("student_loan"):
        parts.append(f"Plan 2 student loan {money(loan_repay, settings)}")
    return (f"Estimate for England, 2026/27 tax year: on {money(gross, settings)} a year, take-home is about "
            f"{money(net, settings)} a year, {money(net / 12, settings)} a month. Deductions: "
            f"{', '.join(parts)}. This is an estimate; tax codes, benefits and salary sacrifice change it.")


def vat(args, settings, adding: bool) -> str:
    amount = _num(args, "amount", "amount")
    rate = _num(args, "rate", "VAT rate", default=20.0, high=100)
    if adding:
        gross = amount * (1 + rate / 100)
        return (f"{money(amount, settings)} plus {_pct(rate)} VAT is {money(gross, settings)} "
                f"(VAT {money(gross - amount, settings)}).")
    net = amount / (1 + rate / 100)
    return (f"{money(amount, settings)} including {_pct(rate)} VAT is {money(net, settings)} before VAT "
            f"(VAT {money(amount - net, settings)}).")


def unit_price(args, settings) -> str:
    items = args.get("items") or []
    if not 2 <= len(items) <= 10:
        raise ValueError("Give me two to ten items to compare, each with a price and size.")
    rows = []
    for i, item in enumerate(items):
        price = _num(item, "price", "price", low=0.0)
        size = _num(item, "size", "size", low=1e-9)
        label = str(item.get("label") or "").strip()[:40] or f"option {i + 1}"
        unit = str(item.get("unit") or "").strip()
        if unit:
            kind, factor, _ = calcunits.find(unit)
        else:
            kind, factor = "items", 1.0
        rows.append((label, kind, price / (size * factor)))
    kinds = {r[1] for r in rows}
    if len(kinds) > 1:
        raise ValueError("Those sizes measure different things, so I can't compare them.")
    per, per_name = PER.get(rows[0][1], (1, "unit"))
    ranked = sorted(rows, key=lambda r: r[2])
    lines = [f"{r[0]}: {money(r[2] * per, settings)} per {per_name}" for r in rows]
    best, next_best = ranked[0], ranked[1]
    if next_best[2] == best[2]:
        return "; ".join(lines) + ". They're the same value."
    saving = (1 - best[2] / next_best[2]) * 100
    return "; ".join(lines) + f". {best[0].capitalize()} is better value, about {_pct(round(saving))} cheaper per {per_name}."


def fuel_cost(args, settings) -> str:
    miles = _num(args, "miles", "distance in miles", low=0.1, high=100_000)
    mpg = _num(args, "mpg", "miles per gallon", low=1, high=1000)
    price = _num(args, "price", "fuel price per litre", low=0.01, high=1000)
    if price > 10:
        price /= 100
    litres = miles / mpg * LITRES_PER_UK_GALLON
    cost = litres * price
    return (f"{fmt(miles)} miles at {fmt(mpg)} mpg uses about {litres:.1f} litres; at "
            f"{money(price, settings)} a litre that's about {money(cost, settings)}.")


ACTIONS = {
    "percent_of": percent_of, "what_percent": percent_is, "percent_change": percent_change, "tip": tip,
    "loan": loan, "savings_growth": savings_growth, "savings_goal": savings_goal, "take_home": take_home,
    "vat_add": lambda a, s: vat(a, s, True), "vat_remove": lambda a, s: vat(a, s, False),
    "unit_price": unit_price, "fuel_cost": fuel_cost,
}


def tool_definitions() -> list[dict]:
    num = {"type": "number"}
    return [{
        "name": "money_maths",
        "description": "Exact money and percentage sums; use instead of working them out yourself. Actions: "
                       "percent_of (percent of amount); what_percent (amount is what % of total); percent_change "
                       "(amount -> total); tip (amount = bill, percent, people to split); loan (amount, rate % a "
                       "year, years: monthly repayment and interest); savings_growth (amount to start, monthly, "
                       "rate, years); savings_goal (total = goal, amount to start, monthly, rate: how long); "
                       "take_home (amount = yearly salary, percent = pension %, student_loan for Plan 2: UK "
                       "2026/27 estimate, say it is an estimate); vat_add / vat_remove (amount, rate default 20); "
                       "unit_price (items with price, size, unit such as g/kg/ml/l, label); fuel_cost (miles, mpg, "
                       "price per litre).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "amount": num, "total": num, "percent": num, "rate": num, "years": num, "monthly": num,
                "people": {"type": "integer"}, "student_loan": {"type": "boolean"},
                "miles": num, "mpg": num, "price": num,
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"price": num, "size": num, "unit": {"type": "string"},
                                       "label": {"type": "string"}},
                        "required": ["price", "size"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"money_maths"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action = ACTIONS.get(args.get("action"))
    if action is None:
        raise ValueError(f"Unknown action. Use one of: {', '.join(ACTIONS)}.")
    return action(args, settings)
