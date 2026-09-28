"""Spreadsheets: simple CSV tables in the memory folders, edited by voice and shown as pop-up tables.

The first row holds the column names. Row numbers count from 1 under that row. Every change keeps the previous
copy as a version (see docs_tools). Totals by group pop up as a table with a bar chart (the documents-summary kind,
drawn by frontend/popup-documents.js).
"""

import csv
import io
import re
from collections import defaultdict
from pathlib import Path

import docs_tools as dt
import memory
import screen
from config import Settings

MAX_ROWS = 5000
MAX_COLUMNS = 30
SHOW_ROWS = 200
SUMMARY_KIND = "documents-summary"
OPS = ["equals", "not_equals", "contains", "greater", "less", "at_least", "at_most"]
screen.EXTRA_KINDS.add(SUMMARY_KIND)


def load(path: Path) -> tuple[list[str], list[list[str]]]:
    rows = list(csv.reader(io.StringIO(dt.read(path).lstrip("﻿"))))
    if not rows:
        raise ValueError(f"{path.name} is empty.")
    head = [c.strip() for c in rows[0]]
    body = [(r + [""] * len(head))[:len(head)] for r in rows[1:] if any(c.strip() for c in r)]
    return head, body


def save(path: Path, head: list[str], rows: list[list[str]]) -> None:
    if len(rows) > MAX_ROWS:
        raise ValueError(f"That spreadsheet is full ({MAX_ROWS} rows).")
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(head)
    writer.writerows(rows)
    dt.write(path, out.getvalue())


def number(value) -> float | None:
    """A number from a cell like '£1,234.50', '12%' or '(30)'; None if it isn't one."""
    text = re.sub(r"[£$€,\s%]|GBP|ZAR|USD|EUR|^R(?=\d)", "", str(value or "")).strip()
    if not re.fullmatch(r"\(?[-+]?(\d+\.?\d*|\.\d+)\)?", text):
        return None
    n = float(text.strip("()"))
    return -n if text.startswith("(") and text.endswith(")") else n


def fmt(n: float) -> str:
    return f"{n:,.0f}" if float(n).is_integer() else f"{n:,.2f}"


def column(head: list[str], name) -> int:
    want = str(name or "").strip().lower()
    for match in (lambda c: c.lower() == want, lambda c: want and want in c.lower()):
        for i, c in enumerate(head):
            if match(c):
                return i
    raise ValueError(f"There's no column called {name}. The columns are {', '.join(head)}.")


def row_index(rows: list, n) -> int:
    try:
        i = int(n)
    except (TypeError, ValueError):
        raise ValueError("Which row number?") from None
    if not 1 <= i <= len(rows):
        raise ValueError(f"There are {len(rows)} rows; pick 1 to {len(rows)}." if rows else "The spreadsheet has no rows.")
    return i - 1


def find_sheet(settings: Settings, args: dict) -> Path:
    return dt.find(settings, args.get("name"), args.get("folder") or "", (".csv",))


def show_sheet(settings: Settings, path: Path, said: str) -> screen.Shown:
    head, rows = load(path)
    more = f" Showing the first {SHOW_ROWS}." if len(rows) > SHOW_ROWS else ""
    c = screen.card("table", path.stem, f"docs-sheet-{dt.rel(settings, path)}", columns=["#", *head],
                    rows=[[str(i), *r] for i, r in enumerate(rows[:SHOW_ROWS], 1)],
                    buttons=[{"label": "Totals", "say": f"Add up the numbers in the spreadsheet {path.stem}."}],
                    text=f"{len(rows)} rows.{more}")
    return screen.Shown(said, c)


# ---- Actions -------------------------------------------------------------------------------------

def create(settings: Settings, args: dict) -> screen.Shown:
    head = [str(c).strip()[:60] for c in (args.get("columns") or []) if str(c).strip()]
    if not head:
        raise ValueError("Which columns should the spreadsheet have?")
    if len(head) > MAX_COLUMNS or len({c.lower() for c in head}) != len(head):
        raise ValueError(f"Give up to {MAX_COLUMNS} columns, each with a different name.")
    title = str(args.get("name") or args.get("title") or "").strip()
    if not title:
        raise ValueError("What should the spreadsheet be called?")
    path = dt.new_path(settings, args.get("folder") or "", title, ".csv")
    save(path, head, [])
    return show_sheet(settings, path, f"Made the spreadsheet {path.stem} with columns {', '.join(head)}.")


def add_row(settings: Settings, args: dict) -> screen.Shown:
    path = find_sheet(settings, args)
    head, rows = load(path)
    values = args.get("values") or {}
    if not values:
        raise ValueError("What goes in the new row?")
    row = [""] * len(head)
    for key, value in values.items():
        row[column(head, key)] = str(value)[:500]
    rows.append(row)
    save(path, head, rows)
    return show_sheet(settings, path, f"Added row {len(rows)} to {path.stem}.")


def update_cell(settings: Settings, args: dict) -> screen.Shown:
    path = find_sheet(settings, args)
    head, rows = load(path)
    i, c = row_index(rows, args.get("row")), column(head, args.get("column"))
    rows[i][c] = str(args.get("value") or "")[:500]
    save(path, head, rows)
    return show_sheet(settings, path, f"Row {i + 1} {head[c]} is now {rows[i][c] or 'empty'}.")


def delete_row(settings: Settings, args: dict) -> screen.Shown | str:
    path = find_sheet(settings, args)
    head, rows = load(path)
    i = row_index(rows, args.get("row"))
    if args.get("confirmed") is not True:
        return (f"Not deleted. Row {i + 1} of {path.stem} is: {', '.join(f'{h} {v}' for h, v in zip(head, rows[i]))}. "
                "Ask the user to confirm, then call again with confirmed true.")
    gone = rows.pop(i)
    save(path, head, rows)
    return show_sheet(settings, path, f"Deleted row {i + 1} ({', '.join(v for v in gone if v)[:80]}).")


def show(settings: Settings, args: dict) -> screen.Shown:
    path = find_sheet(settings, args)
    head, rows = load(path)
    return show_sheet(settings, path, f"{path.stem} has {len(rows)} rows; it's on the screen.")


def stats(settings: Settings, args: dict) -> screen.Shown:
    path = find_sheet(settings, args)
    head, rows = load(path)
    targets = [column(head, args["column"])] if args.get("column") else range(len(head))
    table, said = [], []
    for c in targets:
        nums = [n for r in rows if (n := number(r[c])) is not None]
        if not nums:
            continue
        total = sum(nums)
        table.append([head[c], fmt(total), fmt(total / len(nums)), fmt(min(nums)), fmt(max(nums)), str(len(nums))])
        said.append(f"{head[c]}: total {fmt(total)}, average {fmt(total / len(nums))}, lowest {fmt(min(nums))}, "
                    f"highest {fmt(max(nums))}, {len(nums)} values")
    if not table:
        raise ValueError(f"There are no numbers in {head[targets[0]] if args.get('column') else path.stem}.")
    return screen.Shown(f"{path.stem} ({len(rows)} rows). " + "; ".join(said) + ".",
                        screen.card("table", f"{path.stem}: totals", f"docs-stats-{dt.rel(settings, path)}",
                                    columns=["Column", "Sum", "Average", "Min", "Max", "Count"], rows=table))


def group_totals(settings: Settings, args: dict) -> screen.Shown:
    path = find_sheet(settings, args)
    head, rows = load(path)
    g = column(head, args.get("group_by"))
    c = column(head, args.get("column")) if args.get("column") else None
    totals: dict[str, float] = defaultdict(float)
    names = {}
    for r in rows:
        key = r[g].strip() or "(blank)"
        names.setdefault(key.lower(), key)
        totals[key.lower()] += 1 if c is None else (number(r[c]) or 0)
    if not totals:
        raise ValueError(f"{path.stem} has no rows yet.")
    ordered = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    what = head[c] if c is not None else "Count"
    table = [[names[k], fmt(v)] for k, v in ordered] + [["Total", fmt(sum(totals.values()))]]
    chart = {"type": "bar", "labels": [names[k][:30] for k, _ in ordered[:60]], "values": [v for _, v in ordered[:60]],
             "unit": ""}
    title = f"{path.stem}: {what} by {head[g]}"
    card = screen.card(SUMMARY_KIND, title, f"docs-group-{dt.rel(settings, path)}-{head[g]}",
                       data={"columns": [head[g], what], "rows": table, "chart": chart})
    top = ", ".join(f"{names[k]} {fmt(v)}" for k, v in ordered[:5])
    return screen.Shown(f"{what} by {head[g]}: {top}{' and more' if len(ordered) > 5 else ''}.", card)


def matches(cell: str, op: str, value: str) -> bool:
    a, b = number(cell), number(value)
    if op in ("greater", "less", "at_least", "at_most"):
        if a is None or b is None:
            return False
        return {"greater": a > b, "less": a < b, "at_least": a >= b, "at_most": a <= b}[op]
    same = (a == b) if a is not None and b is not None else cell.strip().lower() == value.strip().lower()
    if op == "equals":
        return same
    if op == "not_equals":
        return not same
    return value.strip().lower() in cell.lower()


def sort_filter(settings: Settings, args: dict) -> screen.Shown:
    path = find_sheet(settings, args)
    head, rows = load(path)
    steps = []
    if args.get("filter_column"):
        f = column(head, args["filter_column"])
        op = args.get("filter_op") or "equals"
        if op not in OPS:
            raise ValueError(f"The filter can be {', '.join(OPS)}.")
        value = str(args.get("filter_value") or "")
        rows = [r for r in rows if matches(r[f], op, value)]
        steps.append(f"{head[f]} {op.replace('_', ' ')} {value}")
    if args.get("sort_by"):
        s = column(head, args["sort_by"])
        filled = [r for r in rows if r[s].strip()]
        numbers = [r for r in filled if number(r[s]) is not None]
        numeric = len(numbers) * 2 >= len(filled) > 0
        first = numbers if numeric else filled
        first.sort(key=(lambda r: number(r[s])) if numeric else (lambda r: r[s].lower()),
                   reverse=bool(args.get("descending")))
        rows = first + [r for r in rows if not any(r is f for f in first)]  # blanks and odd ones last
        steps.append(f"sorted by {head[s]}{' high to low' if args.get('descending') else ''}")
    if not steps:
        raise ValueError("Say how to sort or filter it.")
    title = str(args.get("new_name") or "").strip() or f"{path.stem} ({', '.join(steps)})"[:60]
    out = memory.unique_path(path.parent / f"{memory.safe_name(title, 'spreadsheet name')}.csv")
    save(out, head, rows)
    return show_sheet(settings, out, f"Saved {len(rows)} rows as {out.stem}.")


ACTIONS = {"create": create, "add_row": add_row, "update_cell": update_cell, "delete_row": delete_row, "show": show,
           "totals": stats, "group_totals": group_totals, "sort_filter": sort_filter}


def tool_definitions() -> list[dict]:
    return [{
        "name": "spreadsheet",
        "description": "The user's simple spreadsheets (CSV tables in their memory folders), shown as pop-up tables. "
                       "action: 'create' a spreadsheet with columns; 'add_row'; 'update_cell' (row number and "
                       "column); 'delete_row' (ask first; set confirmed true only after the user says yes); 'show' it; "
                       "'totals' sum, average, min, max and count of a column (or every number column); "
                       "'group_totals' adds up a column for each value of another (e.g. spending by category) "
                       "with a bar chart; 'sort_filter' sorts and/or filters it into a new spreadsheet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "name": {"type": "string", "description": "The spreadsheet's name (create: the new name)."},
                "folder": {"type": "string", "description": "Memory folder, e.g. 'Work'. Leave out: new ones go in "
                                                            "Documents, and spreadsheets are looked for everywhere."},
                "columns": {"type": "array", "items": {"type": "string"}, "description": "create: column names."},
                "values": {"type": "object", "additionalProperties": {"type": "string"},
                           "description": "add_row: {column: value}."},
                "row": {"type": "integer", "description": "Row number, 1 is the first row under the headings."},
                "column": {"type": "string", "description": "update_cell, totals, group_totals: the column."},
                "value": {"type": "string", "description": "update_cell: the new value."},
                "group_by": {"type": "string", "description": "group_totals: the column to group by."},
                "sort_by": {"type": "string"},
                "descending": {"type": "boolean"},
                "filter_column": {"type": "string"},
                "filter_op": {"type": "string", "enum": OPS},
                "filter_value": {"type": "string"},
                "new_name": {"type": "string", "description": "sort_filter: name for the new spreadsheet."},
                "confirmed": {"type": "boolean", "description": "delete_row: true only after the user said yes."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"spreadsheet"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = ACTIONS.get(args.get("action"))
    if not action:
        raise ValueError(f"Pick an action: {', '.join(ACTIONS)}.")
    return action(settings, args)
