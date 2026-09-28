"""Budgets and money reports built on the spending log and payslips from money.py.

Monthly budgets per spending category, over-budget warnings, spending trends, likely subscriptions hiding in the
spending log, a monthly money report, a UK tax-year summary (6 April to 5 April) and a CSV export.
Budgets live in finance-budgets.json in the memory folder; amounts are in the user's currency.
"""

import csv
import io
import re
import statistics
from collections import defaultdict
from datetime import date

import finance_store as fs
import homestore as hs
import memory
import money
import screen
from config import Settings

MAX_BUDGETS = 40


def budget_set(settings: Settings, category, value, confirmed: bool) -> str:
    category = hs.need(category, "spending category", 30).lower()
    found = fs.budgets(settings)
    number = fs.amount(value, "budget")
    if number == 0:
        if category not in found:
            return f"There's no {category} budget."
        if not confirmed:
            return f"Ask the user to confirm removing the {category} budget, then call again with confirmed true."
        del found[category]
        hs.save(settings, fs.BUDGETS, found)
        return f"Removed the {category} budget."
    if category not in found and len(found) >= MAX_BUDGETS:
        raise ValueError("That's a lot of budgets; remove one first.")
    found[category] = number
    hs.save(settings, fs.BUDGETS, found)
    return f"The {category} budget is {fs.cash(number, settings)} a month."


def _meters(settings: Settings, month: str) -> list[dict]:
    spent = fs.spent_by_category(settings, month)
    return [fs.meter(c, spent.get(c, 0.0), b, settings, say=f"How much is left in my {c} budget?")
            for c, b in sorted(fs.budgets(settings).items())]


def budget_status(settings: Settings, category, month) -> screen.Shown | str:
    month = fs.month_of(month, hs.today())
    found = fs.budgets(settings)
    if not found:
        return "No budgets set yet. Say something like 'set a food budget of 300 a month'."
    spent = fs.spent_by_category(settings, month)
    if category:
        key = fs.key_of(found, str(category).lower(), "budget")
        left = found[key] - spent.get(key, 0.0)
        said = (f"You've {fs.cash(left, settings)} left for {key} in {fs.month_name(month)}." if left >= 0 else
                f"You're {fs.cash(-left, settings)} over the {key} budget in {fs.month_name(month)}.")
    else:
        total = sum(found.values())
        used = sum(spent.get(c, 0.0) for c in found)
        said = f"You've used {fs.cash(used, settings)} of {fs.cash(total, settings)} budgeted in {fs.month_name(month)}."
    return fs.board(said, f"Budgets {fs.month_name(month)}", "finance-budgets",
                    [fs.section("meters", "Spent vs budget", rows=_meters(settings, month))],
                    buttons=[{"label": "Over budget?", "say": "Am I over budget anywhere?"}])


def over_budget(settings: Settings, month) -> str | screen.Shown:
    month = fs.month_of(month, hs.today())
    spent = fs.spent_by_category(settings, month)
    warn = []
    for c, b in sorted(fs.budgets(settings).items()):
        used = spent.get(c, 0.0)
        if used > b:
            warn.append((c, True, f"{c}: {fs.cash(used - b, settings)} over ({fs.cash(used, settings)} of {fs.cash(b, settings)})"))
        elif b and used >= 0.9 * b:
            warn.append((c, False, f"{c}: nearly there, {fs.cash(b - used, settings)} left"))
    if not fs.budgets(settings):
        return "No budgets set yet."
    if not warn:
        return f"You're within every budget in {fs.month_name(month)}."
    over = sum(1 for _, is_over, _ in warn if is_over)
    said = f"{over} over budget, {len(warn) - over} close to the limit: " + "; ".join(w[2] for w in warn) + "."
    return screen.Shown(said, screen.card("list", f"Budget warnings {fs.month_name(month)}", "finance-warnings",
                                          items=[{"label": line, "say": f"How much is left in my {c} budget?"}
                                                 for c, _, line in warn]))


def trends(settings: Settings, category) -> screen.Shown | str:
    this = hs.today().strftime("%Y-%m")
    months = [fs.month_back(this, n) for n in range(5, -1, -1)]
    per = {m: fs.spent_by_category(settings, m) for m in months}
    cats = sorted({c for m in months for c in per[m]})
    if not cats:
        return "There's no spending logged in the last six months."
    labels = [date(int(m[:4]), int(m[5:]), 1).strftime("%b") for m in months]
    if category:
        cat = hs.find(cats, str(category).lower())
        if cat is None:
            return f"No {hs.clean(category)} spending in the last six months."
        values = [per[m].get(cat, 0.0) for m in months]
        said = f"{cat.title()} spending over six months, from {fs.cash(values[0], settings)} to {fs.cash(values[-1], settings)} this month so far."
        return fs.board(said, f"{cat.title()} spending", f"finance-trend-{cat}",
                        [fs.chart(labels, values, "bar", title=f"{cat} per month")])
    changes = []
    last, before = months[-2], months[:-2]
    for c in cats:
        avg = sum(per[m].get(c, 0.0) for m in before) / len(before)
        changes.append((per[last].get(c, 0.0) - avg, c, avg))
    changes.sort(key=lambda x: -abs(x[0]))
    notes = [f"{c}: {'up' if d > 0 else 'down'} {fs.cash(abs(d), settings)} in {fs.month_name(last)} vs the "
             f"earlier average of {fs.cash(avg, settings)}" for d, c, avg in changes[:3] if abs(d) >= 0.01]
    body = [[c] + [f"{per[m].get(c, 0.0):,.0f}" for m in months] for c in cats]
    totals = [sum(per[m].values()) for m in months]
    said = ("Biggest changes: " + "; ".join(notes) + ".") if notes else "Spending has been steady."
    return fs.board(said, "Spending trends", "finance-trends",
                    [fs.chart(labels, totals, "bar", title="Total per month"),
                     fs.table(["Category"] + labels, body, f"By category ({settings.currency})"),
                     fs.section("list", "Biggest changes", items=[{"label": n} for n in notes])])


def recurring(settings: Settings) -> screen.Shown | str:
    groups = defaultdict(list)
    for s in fs.spending(settings):
        groups[re.sub(r"\s+", " ", str(s.get("what") or "")).strip().lower()].append(s)
    found = []
    for what, entries in groups.items():
        months = {e["date"][:7] for e in entries}
        if what in ("", "something") or len(months) < 2:
            continue
        amounts = [e["amount"] for e in entries]
        typical = statistics.median(amounts)
        if max(amounts) - min(amounts) <= max(1.0, typical * 0.1):
            found.append((what, typical, len(months), max(e["date"] for e in entries)))
    if not found:
        return "I can't see any repeated payments that look like subscriptions."
    found.sort(key=lambda x: -x[1])
    said = "Likely subscriptions: " + "; ".join(f"{w} about {fs.cash(a, settings)} ({m} months)"
                                                  for w, a, m, _ in found) + "."
    items = [{"label": f"{w} - about {fs.cash(a, settings)}, seen in {m} months, last {d}",
              "say": f"Add {w} to my subscriptions at {a:.2f} a month."} for w, a, m, d in found]
    return screen.Shown(said, screen.card("list", "Likely subscriptions", "finance-recurring", items=items))


def _pot_changes(settings: Settings, start: str, end: str) -> dict[str, float]:
    changes = defaultdict(float)
    for name, pot in fs.rows(settings, fs.POTS).items():
        for h in pot.get("history") or []:
            if isinstance(h, dict) and start <= str(h.get("date", "")) <= end:
                changes[name] += float(h.get("amount") or 0)
    return dict(changes)


def report(settings: Settings, month) -> screen.Shown:
    month = fs.month_of(month, hs.today())
    income = sum(p["net"] for p in money.load(settings)["payslips"] if p.get("month") == month)
    spent = fs.spent_by_category(settings, month)
    total = sum(spent.values())
    pots = _pot_changes(settings, f"{month}-01", f"{month}-31")
    saved = sum(pots.values())
    sections = [fs.stats([("Income", fs.cash(income, settings)), ("Spent", fs.cash(total, settings)),
                          ("Left over", fs.cash(income - total, settings)), ("Into savings", fs.cash(saved, settings))])]
    if spent:
        cats = sorted(spent.items(), key=lambda kv: -kv[1])
        sections.append(fs.chart([c for c, _ in cats], [v for _, v in cats], title="Spending by category"))
    if fs.budgets(settings):
        sections.append(fs.section("meters", "Budgets", rows=_meters(settings, month)))
    if pots:
        sections.append(fs.table(["Pot", "Change"], [[p, f"{v:+,.2f}"] for p, v in sorted(pots.items())], "Savings pots"))
    said = (f"In {fs.month_name(month)} you took home {fs.cash(income, settings)}, spent {fs.cash(total, settings)}"
            f" and put {fs.cash(saved, settings)} into savings pots.")
    return fs.board(said, f"Money report {fs.month_name(month)}", f"finance-report-{month}", sections)


def tax_year(settings: Settings, year) -> screen.Shown:
    today = hs.today()
    start = int(hs.number(year, "tax year", 2000, 2100)) if year else (today.year if today >= date(today.year, 4, 6) else today.year - 1)
    first, last = date(start, 4, 6), date(start + 1, 4, 5)
    months = [fs.month_back(f"{start + 1}-03", n) for n in range(11, -1, -1)]
    slips = [p for p in money.load(settings)["payslips"] if p.get("month") in months]
    by_month = defaultdict(float)
    for p in slips:
        by_month[p["month"]] += p["net"]
    take_home = sum(by_month.values())
    spent = sum(s["amount"] for s in fs.spending(settings) if first.isoformat() <= s["date"][:10] <= last.isoformat())
    saved = sum(_pot_changes(settings, first.isoformat(), last.isoformat()).values())
    label = f"{start}/{str(start + 1)[2:]}"
    said = (f"Tax year {label}: take-home {fs.cash(take_home, settings)}, spending {fs.cash(spent, settings)}, "
            f"saved into pots {fs.cash(saved, settings)}.")
    extra = []
    for field in ("gross", "tax"):
        if any(field in p for p in slips):
            extra.append((field.title(), fs.cash(sum(p.get(field, 0) for p in slips), settings)))
    labels = [date(int(m[:4]), int(m[5:]), 1).strftime("%b") for m in months]
    return fs.board(said, f"Tax year {label}", f"finance-taxyear-{start}", [
        fs.stats([("Take-home", fs.cash(take_home, settings)), ("Spending", fs.cash(spent, settings)),
                  ("Saved", fs.cash(saved, settings)), ("Payslips", str(len(slips)))] + extra,
                 f"6 April {start} to 5 April {start + 1}"),
        fs.chart(labels, [by_month.get(m, 0.0) for m in months], title="Take-home per month")])


def _plain(value) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[,\r\n\"]+", " ", str(value))).strip()


def export(settings: Settings, folder) -> screen.Shown:
    data = money.load(settings)
    rows = [["spending", s.get("date", ""), _plain(s.get("what", "")), _plain(s.get("category", "")), f"{s['amount']:.2f}"]
            for s in fs.spending(settings)]
    rows += [["payslip", p.get("month", ""), _plain(p.get("employer", "")), "take-home", f"{float(p.get('net', 0)):.2f}"]
             for p in data["payslips"]]
    for name, pot in fs.rows(settings, fs.POTS).items():
        rows += [["savings pot", h.get("date", ""), _plain(name), "deposit" if h.get("amount", 0) >= 0 else "withdrawal",
                  f"{float(h.get('amount', 0)):.2f}"] for h in pot.get("history") or [] if isinstance(h, dict)]
    if not rows:
        raise ValueError("There's no money data to export yet.")
    rows.sort(key=lambda r: r[1])
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["type", "date", "description", "category", f"amount {settings.currency}"])
    writer.writerows(rows)
    where = memory.folder(settings, hs.clean(folder)) if hs.clean(folder) else memory.folder(settings, 3)
    path = memory.unique_path(where / f"money export {hs.today().isoformat()}.csv")
    path.write_text(out.getvalue(), encoding="utf-8")
    return screen.Shown(f"Exported {hs.plural(len(rows), 'row')} to {path.name} in {where.name}.",
                        screen.file_card(settings, path))


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "money_budgets",
        "description": "Monthly spending budgets and money reports from the money log. budget_set (category, "
                       "amount a month; amount 0 removes it, only with confirmed true after the user agrees). "
                       "budget_left: how much is left for a category (or all) this month, with spent-vs-budget "
                       "bars. over_budget: warnings for budgets over or nearly over. trends: spending per month for "
                       "the last 6 months and the biggest changes (optional category). recurring: repeated "
                       "payments that look like subscriptions. report: monthly money report (income, spending by "
                       "category, budgets, savings). tax_year: UK tax year summary, 6 April to 5 April (year = the "
                       "starting year). export: save money data as a CSV spreadsheet in a memory folder and show it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["budget_set", "budget_left", "over_budget", "trends",
                                                      "recurring", "report", "tax_year", "export"]},
                "category": text,
                "amount": {"type": "number"},
                "month": {"type": "string", "description": "YYYY-MM; default this month."},
                "year": {"type": "integer"},
                "folder": {"type": "string", "description": "export: memory folder, default Personal."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"money_budgets"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    actions = {
        "budget_set": lambda: budget_set(settings, a("category"), a("amount"), bool(a("confirmed"))),
        "budget_left": lambda: budget_status(settings, a("category"), a("month")),
        "over_budget": lambda: over_budget(settings, a("month")),
        "trends": lambda: trends(settings, a("category")),
        "recurring": lambda: recurring(settings),
        "report": lambda: report(settings, a("month")),
        "tax_year": lambda: tax_year(settings, a("year")),
        "export": lambda: export(settings, a("folder")),
    }
    if a("action") not in actions:
        raise ValueError("Unknown budgets action.")
    return actions[a("action")]()
