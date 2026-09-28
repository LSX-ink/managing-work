"""Money: payslips and spending, logged by voice, summed up on request.

Kept in money.json in the memory folder. Amounts are in the user's own currency (JARVIS_CURRENCY, default GBP).
Also converts currencies with the free European Central Bank rates from frankfurter.dev (no key).
"""

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

import httpx

import memory
from config import Settings

MAX_ENTRIES = 5000
RATES_URL = "https://api.frankfurter.dev/v1/latest"


def path(settings: Settings) -> Path:
    return memory.root(settings) / "money.json"


def load(settings: Settings) -> dict:
    try:
        found = json.loads(path(settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        found = {}
    if not isinstance(found, dict):
        found = {}
    return {"payslips": list(found.get("payslips") or []), "spending": list(found.get("spending") or [])}


def save(settings: Settings, data: dict) -> None:
    if len(data["payslips"]) + len(data["spending"]) > MAX_ENTRIES:
        raise ValueError("The money log is full.")
    path(settings).parent.mkdir(parents=True, exist_ok=True)
    path(settings).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _amount(value, what: str) -> float:
    try:
        number = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValueError(f"The {what} must be a number.") from None
    if not 0 <= number < 10_000_000:
        raise ValueError(f"That {what} doesn't look right.")
    return number


def _month(value: str | None, today: date) -> str:
    value = (value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", value):
        return value[:7]
    if value:
        raise ValueError("Give the month as YYYY-MM, e.g. 2026-08.")
    return today.strftime("%Y-%m")


def _money(n: float, cur: str) -> str:
    return f"{n:,.2f} {cur}"


def log_payslip(settings: Settings, args: dict, today: date | None = None) -> str:
    today = today or date.today()
    data = load(settings)
    month = _month(args.get("month"), today)
    employer = re.sub(r"\s+", " ", str(args.get("employer") or "")).strip()[:60]
    slip = {"month": month, "employer": employer, "net": _amount(args.get("net"), "take-home pay")}
    for field in ("gross", "tax"):
        if args.get(field) is not None:
            slip[field] = _amount(args[field], field)
    # One payslip per employer per month: logging it again corrects it.
    data["payslips"] = [p for p in data["payslips"]
                        if not (p.get("month") == month and p.get("employer", "").lower() == employer.lower())]
    data["payslips"].append(slip)
    data["payslips"].sort(key=lambda p: p.get("month", ""))
    save(settings, data)
    who = f" from {employer}" if employer else ""
    return f"Logged the {month} payslip{who}: take-home {_money(slip['net'], settings.currency)}."


def log_spend(settings: Settings, args: dict, today: date | None = None) -> str:
    today = today or date.today()
    data = load(settings)
    what = re.sub(r"\s+", " ", str(args.get("what") or "")).strip()[:60] or "something"
    category = re.sub(r"\s+", " ", str(args.get("category") or "")).strip().lower()[:30] or "other"
    spend = {"date": today.isoformat(), "amount": _amount(args.get("amount"), "amount"), "what": what,
             "category": category}
    data["spending"].append(spend)
    save(settings, data)
    month = today.strftime("%Y-%m")
    total = sum(s["amount"] for s in data["spending"] if s.get("date", "").startswith(month))
    return f"Logged {_money(spend['amount'], settings.currency)} on {what}. This month so far: {_money(total, settings.currency)}."


def undo(settings: Settings) -> str:
    data = load(settings)
    if not data["spending"]:
        return "There's no spending to remove."
    gone = data["spending"].pop()
    save(settings, data)
    return f"Removed {_money(gone['amount'], settings.currency)} on {gone['what']}."


def summary(settings: Settings, today: date | None = None) -> str:
    today = today or date.today()
    data, cur = load(settings), settings.currency
    parts = []
    slips = data["payslips"][-12:]
    if slips:
        lines = [f"- {p['month']}{' ' + p['employer'] if p.get('employer') else ''}: take-home {_money(p['net'], cur)}"
                 + (f", gross {_money(p['gross'], cur)}" if "gross" in p else "")
                 + (f", tax {_money(p['tax'], cur)}" if "tax" in p else "") for p in slips]
        nets = [p["net"] for p in slips]
        lines.append(f"Average take-home over these {len(nets)}: {_money(sum(nets) / len(nets), cur)}; "
                     f"total {_money(sum(nets), cur)}.")
        parts.append("Payslips (oldest first):\n" + "\n".join(lines))
    month = today.strftime("%Y-%m")
    last = (today.replace(day=1).toordinal() - 1)
    last_month = date.fromordinal(last).strftime("%Y-%m")
    for label, m in (("This month", month), ("Last month", last_month)):
        spent = [s for s in data["spending"] if s.get("date", "").startswith(m)]
        if spent:
            by = defaultdict(float)
            for s in spent:
                by[s.get("category") or "other"] += s["amount"]
            cats = ", ".join(f"{c} {_money(v, cur)}" for c, v in sorted(by.items(), key=lambda kv: -kv[1]))
            parts.append(f"{label} ({m}) spending: {_money(sum(by.values()), cur)} ({cats}).")
    return "\n".join(parts) or "Nothing logged yet."


async def convert(http: httpx.AsyncClient, amount, source: str, target: str) -> str:
    amount = _amount(amount, "amount")
    source, target = source.strip().upper(), target.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", source) or not re.fullmatch(r"[A-Z]{3}", target):
        raise ValueError("Use three-letter currency codes, e.g. GBP, USD, ZAR.")
    if source == target:
        return f"{_money(amount, source)} is {_money(amount, target)}."
    r = await http.get(RATES_URL, params={"amount": amount, "from": source, "to": target}, timeout=10)
    if r.status_code == 404:
        raise ValueError(f"The exchange-rate service doesn't know {source} or {target}.")
    r.raise_for_status()
    body = r.json()
    value = (body.get("rates") or {}).get(target)
    if value is None:
        raise ValueError(f"No rate for {target}.")
    return f"{_money(amount, source)} is {_money(float(value), target)} (European Central Bank rate from {body.get('date')})."


def tool_definitions() -> list[dict]:
    num = {"type": "number"}
    return [
        {
            "name": "money",
            "description": "The user's money log. action 'payslip' logs a payslip (month YYYY-MM, employer, net = "
                           "take-home, optional gross and tax; logging the same month and employer again corrects "
                           "it). 'spend' logs spending today (amount, what, category such as food, transport, "
                           "bills, fun). 'undo' removes the last spending entry. 'summary' gives recent payslips "
                           "with averages and this and last month's spending by category. After reading payslip "
                           "PDFs with read_document, log each one here.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["payslip", "spend", "undo", "summary"]},
                    "month": {"type": "string"}, "employer": {"type": "string"},
                    "net": num, "gross": num, "tax": num,
                    "amount": num, "what": {"type": "string"}, "category": {"type": "string"},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "convert_currency",
            "description": "Convert money between currencies at today's European Central Bank rate.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": num,
                    "from": {"type": "string", "description": "Three-letter code, e.g. GBP."},
                    "to": {"type": "string", "description": "Three-letter code, e.g. ZAR."},
                },
                "required": ["amount", "from", "to"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {"money", "convert_currency"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient) -> str:
    if name == "convert_currency":
        return await convert(http, args.get("amount"), args.get("from") or "", args.get("to") or "")
    action = args.get("action")
    if action == "payslip":
        return log_payslip(settings, args)
    if action == "spend":
        return log_spend(settings, args)
    if action == "undo":
        return undo(settings)
    return summary(settings)
