"""Looking at trackers: a chart with a goal line and stats, a year in pixels, this week or month against the last,
a correlation check between two trackers, a monthly review of every tracker and a personal dashboard.

Charts can also read the other logs (water, sleep, mood, steps, spending, habits). The dashboard's choice is kept
in trackers-dashboard.json in the memory folder.
"""

import math
from datetime import date, timedelta

import habits
import screen
import trackers_store as store
from config import Settings

screen.EXTRA_KINDS.update({"trackers-chart", "trackers-pixels", "trackers-dashboard"})

MAX_TILES = 6
CAUTION = "This only shows the two tend to move together; it doesn't mean one causes the other."


def _chart_card(name: str, info: dict, values: dict, days: list[date], text: str, card_id: str, buttons=None) -> dict:
    kind = "line" if info["type"] in ("rating", "number") else "bar"
    return screen.card("trackers-chart", name, card_id, text=text, buttons=buttons, data={
        "type": kind, "labels": [d.strftime("%d %b") for d in days],
        "values": [values.get(d.isoformat()) for d in days], "unit": store.unit_of(info),
        "goal": info.get("goal"), "max": 5 if info["type"] == "rating" else 1 if info["type"] == "yes_no" else None})


def chart(settings: Settings, wanted: str, days: int):
    days = days if days in (7, 30, 90) else 30
    name, info, values = store.series(settings, wanted)
    span = store.days_back(store.today(), days)
    if info["type"] == "text":
        notes = store.trackers(settings)["notes"].get(name, {})
        items = [f"{d.isoformat()}: {notes[d.isoformat()]}" for d in reversed(span) if d.isoformat() in notes]
        return screen.Shown(f"{len(items)} notes in {name} over {days} days.",
                            screen.card("list", f"{name}, last {days} days", f"trackers-chart-{name}", items=items))
    s = store.stats(values, info, span)
    if not s["logged"]:
        return f"Nothing logged in {name} in the last {days} days."
    rows = [["Average", store.fmt(s["average"], info)], ["Lowest", store.fmt(s["min"], info)],
            ["Highest", store.fmt(s["max"], info)], ["Days logged", f"{s['logged']} of {days}"]]
    if info["type"] in store.ADD_UP and info.get("per_day") != "latest":
        rows.insert(0, ["Total", store.fmt(s["total"], info)])
    if info["type"] == "yes_no":
        rows = [["Yes days", f"{s['total']:g} of {s['logged']} logged"]]
    text = f"{name} over {days} days: average {store.fmt(s['average'], info)}"
    if "goal_days" in s:
        rows += [["Goal met", f"{s['goal_days']} days"], ["Goal streak", f"{s['streak']} days"]]
        text += f", goal met {s['goal_days']} days, streak {s['streak']}"
    buttons = [{"label": f"{n} days", "say": f"Show my {name} chart for {n} days."} for n in (7, 30, 90) if n != days]
    card = _chart_card(name, info, values, span, "", f"trackers-chart-{name}", buttons)
    card["data"]["stats"] = rows
    card["title"] = f"{name}, last {days} days"
    return screen.Shown(text + ".", card)


def _level(value, info: dict, top: float) -> int | None:
    if value is None:
        return None
    if info["type"] == "rating":
        return max(1, min(5, round(value)))
    if info["type"] in ("yes_no", "text"):
        return 5 if value else 0
    return 0 if value <= 0 else max(1, min(5, math.ceil(value / top * 5))) if top > 0 else 0


def pixels_card(title: str, card_id: str, start: date, levels: list, words: dict, notes: dict, legend: list,
                text: str = "", buttons=None) -> dict:
    """Day squares from start: levels 0-5 (None: nothing), words and notes by day shown when one is clicked."""
    cells = []
    for i, level in enumerate(levels):
        day = (start + timedelta(days=i)).isoformat()
        cell = {"d": day, "v": level}
        if day in words:
            cell["t"] = words[day]
        if day in notes:
            cell["n"] = notes[day]
        cells.append(cell)
    return screen.card("trackers-pixels", title, card_id, text=text, buttons=buttons,
                       data={"cells": cells, "offset": start.weekday(), "legend": legend})


def year_pixels(settings: Settings, wanted: str):
    data = store.trackers(settings)
    name, info, values = store.series(settings, wanted, data)
    notes = data["notes"].get(name, {})
    span = store.days_back(store.today(), 365)
    top = max(values.values(), default=0)
    levels = [_level(values.get(d.isoformat(), 1 if d.isoformat() in notes else None), info, top) for d in span]
    legend = {"rating": ["1", "5"], "yes_no": ["no", "yes"]}.get(info["type"], ["low", "high"])
    logged = sum(v is not None for v in levels)
    words = {d: store.fmt(v, info) for d, v in values.items()} if info["type"] != "text" else {}
    card = pixels_card(f"{name}: year in pixels", f"trackers-pixels-{name}", span[0], levels, words, notes, legend,
                       "Click a day to see its value and note.")
    return screen.Shown(f"Your year of {name} is on the screen: {logged} days logged.", card)


def _period(kind: str, today: date) -> tuple[list[date], list[date], str]:
    if kind == "month":
        start = today.replace(day=1)
        last_end = start - timedelta(days=1)
        last = [last_end.replace(day=1) + timedelta(days=i) for i in range(last_end.day)]
        return last, [start + timedelta(days=i) for i in range((today - start).days + 1)], "month"
    start = today - timedelta(days=today.weekday())
    return ([start - timedelta(days=7 - i) for i in range(7)],
            [start + timedelta(days=i) for i in range((today - start).days + 1)], "week")


def _change(old, new) -> str:
    if old is None or new is None:
        return "-"
    if not old:
        return "new" if new else "same"
    return f"{(new - old) / abs(old) * 100:+.0f}%"


def compare(settings: Settings, wanted: str, period: str):
    name, info, values = store.series(settings, wanted)
    last, this, word = _period(period, store.today())
    a, b = store.stats(values, info, last), store.stats(values, info, this)
    adds = info["type"] in store.ADD_UP and info.get("per_day") != "latest"
    rows = []
    if adds or info["type"] == "yes_no":
        rows.append(["Total", store.fmt(a["total"], info) if a["logged"] else "-",
                     store.fmt(b["total"], info) if b["logged"] else "-", _change(a["total"], b["total"])])
    rows.append(["Average a day", store.fmt(a["average"], info), store.fmt(b["average"], info),
                 _change(a["average"], b["average"])])
    rows.append(["Days logged", str(a["logged"]), str(b["logged"]), ""])
    if "goal_days" in a:
        rows.append(["Goal met", f"{a['goal_days']} days", f"{b['goal_days']} days", ""])
    key = "total" if adds else "average"
    if not b["logged"] and not a["logged"]:
        return f"Nothing logged in {name} this {word} or last {word}."
    text = (f"{name}: {store.fmt(b[key], info) if b['logged'] else 'nothing'} this {word} so far, against "
            f"{store.fmt(a[key], info) if a['logged'] else 'nothing'} last {word}.")
    other = "week" if word == "month" else "month"
    card = screen.card("table", f"{name}: this {word} vs last", f"trackers-compare-{name}", text=text,
                       columns=["", f"Last {word}", f"This {word}", "Change"], rows=rows,
                       buttons=[{"label": f"By {other}", "say": f"Compare my {name} this {other} with last {other}."}])
    return screen.Shown(text, card)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not sx or not sy:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def strength(r: float) -> str:
    size = abs(r)
    if size < 0.1:
        return "no real link"
    word = "a weak" if size < 0.3 else "a moderate" if size < 0.5 else "a strong"
    return f"{word} {'positive' if r > 0 else 'negative'} link"


def correlate(settings: Settings, first: str, second: str, days: int):
    data = store.trackers(settings)
    a_name, a_info, a = store.series(settings, first, data)
    b_name, b_info, b = store.series(settings, second, data)
    if a_name == b_name:
        raise ValueError("Pick two different trackers.")
    days = days if days in (30, 90, 365) else 90
    span = [d.isoformat() for d in store.days_back(store.today(), days)]
    both = [d for d in span if d in a and d in b]
    if len(both) < 5:
        raise ValueError(f"I need at least 5 days with both {a_name} and {b_name} logged; there are {len(both)}.")
    r = pearson([a[d] for d in both], [b[d] for d in both])
    if r is None:
        raise ValueError("One of them never changes on those days, so there's nothing to compare.")
    how = "higher" if r > 0 else "lower"
    meaning = "" if abs(r) < 0.1 else f" On days with more {a_name}, {b_name} tended to be {how}."
    text = (f"Over {len(both)} days with both logged, {a_name} and {b_name} show {strength(r)} "
            f"(correlation {r:+.2f}).{meaning} {CAUTION}")
    rows = [[d, store.fmt(a[d], a_info), store.fmt(b[d], b_info)] for d in reversed(both[-60:])]
    card = screen.card("table", f"{a_name} and {b_name}", f"trackers-correlate-{a_name}-{b_name}", text=text,
                       columns=["Day", a_name, b_name], rows=rows)
    return screen.Shown(text, card)


def month_review(settings: Settings, month: str):
    today = store.today()
    try:
        start = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
    except ValueError:
        raise ValueError("Give the month as YYYY-MM, e.g. 2026-08.") from None
    end = min(today, (start + timedelta(days=32)).replace(day=1) - timedelta(days=1))
    if start > today:
        raise ValueError("That month hasn't started yet.")
    span = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    data = store.trackers(settings)
    rows = []
    for name, info in data["trackers"].items():
        values = data["values"].get(name, {})
        s = store.stats(values, info, span)
        adds = info["type"] in store.ADD_UP and info.get("per_day") != "latest"
        total = store.fmt(s["total"], info) if adds and s["logged"] else f"{s['total']:g} yes" if info["type"] == "yes_no" else "-"
        best = max((d for d in span if d.isoformat() in values), key=lambda d: values[d.isoformat()], default=None)
        rows.append([name, str(s["logged"]), total, store.fmt(s["average"], info) if info["type"] != "text" else "-",
                     f"{s['goal_days']} days" if "goal_days" in s else "-",
                     f"{best.day} ({store.fmt(values[best.isoformat()], info)})" if best and info["type"] != "text" else "-"])
    if not rows:
        return "No trackers yet."
    label = start.strftime("%B %Y")
    prev = (start - timedelta(days=1)).strftime("%Y-%m")
    card = screen.card("table", f"Trackers: {label}", "trackers-month", rows=rows,
                       columns=["Tracker", "Days", "Total", "Average", "Goal met", "Top day"],
                       buttons=[{"label": "Month before", "say": f"Show my trackers' monthly review for {prev}."}])
    logged = sum(1 for r in rows if r[1] != "0")
    return screen.Shown(f"{label}: {logged} of {len(rows)} trackers have entries.", card)


def dashboard_set(settings: Settings, items: list) -> str:
    data = store.trackers(settings)
    chosen = []
    for wanted in (items or [])[:MAX_TILES]:
        name = store.series(settings, str(wanted), data)[0]
        if name not in chosen:
            chosen.append(name)
    if not chosen:
        raise ValueError(f"Pick up to {MAX_TILES} trackers, or water, sleep, mood, steps, spending or habits.")
    store.save(settings, "dashboard", {"items": chosen})
    return f"Your dashboard shows {', '.join(chosen)}."


def _tile(settings: Settings, name: str, data: dict, today: date) -> dict:
    name, info, values = store.series(settings, name, data)
    span = store.days_back(today, 14)
    now = values.get(today.isoformat())
    tile = {"name": name, "today": store.fmt(now, info) if now is not None else "nothing yet",
            "labels": [d.strftime("%d %b") for d in span], "values": [values.get(d.isoformat()) for d in span],
            "goal": info.get("goal"), "say": f"Show my {name} chart."}
    if info.get("goal") is not None:
        tile["extra"] = f"goal {store.fmt(info['goal'], info)}, streak {store.goal_streak(values, info, today)}"
    if name == "spending":
        month = today.strftime("%Y-%m")
        tile["extra"] = f"this month {sum(v for d, v in values.items() if d.startswith(month)):,.2f} {settings.currency}"
    if name == "habits":
        found = habits.load(settings)
        best = max(found.items(), key=lambda kv: habits.streak(kv[1], today), default=None)
        tile["today"] = f"{now or 0:g} of {len(found)} done"
        if best:
            tile["extra"] = f"best streak: {best[0]}, {habits.streak(best[1], today)} days"
    return tile


def dashboard(settings: Settings):
    data = store.trackers(settings)
    chosen = store.load(settings, "dashboard", {}).get("items") or list(data["trackers"])[:MAX_TILES]
    if not chosen:
        return "Your dashboard is empty. Create a tracker, or say which ones to show, e.g. 'put water and sleep on my dashboard'."
    today = store.today()
    tiles = []
    for name in chosen:
        try:
            tiles.append(_tile(settings, name, data, today))
        except ValueError:
            continue
    card = screen.card("trackers-dashboard", "My dashboard", "trackers-dashboard", data={"tiles": tiles},
                       buttons=[{"label": "Month review", "say": "Show my trackers' monthly review."}])
    return screen.Shown(f"Your dashboard: {', '.join(t['name'] + ' ' + t['today'] for t in tiles)}.", card)


ACTIONS = ["chart", "year_pixels", "compare", "correlate", "month_review", "dashboard", "dashboard_set"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "tracker_charts",
        "description": "See the user's trackers (and water, sleep, mood, steps, spending, habits) as pop-ups. chart: "
                       "a tracker over the last 7, 30 or 90 days with its goal line and stats (average, min, max, "
                       "total, goal streak). year_pixels: a year-in-pixels grid coloured by value; click a day for "
                       "its note. compare: this week vs last week, or period month. correlate: do two trackers move "
                       "together (tracker and other), with a caution that it isn't cause. month_review: every "
                       "tracker's month in one table. dashboard: the personal dashboard with mini charts and today's "
                       "values; dashboard_set picks up to 6 items for it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "tracker": {"type": "string", "description": "Tracker name as the user says it."},
                "other": {"type": "string", "description": "correlate: the second tracker."},
                "days": {"type": "integer", "enum": [7, 30, 90, 365],
                         "description": "chart: 7, 30 or 90; correlate: 30, 90 or 365."},
                "period": {"type": "string", "enum": ["week", "month"]},
                "month": {"type": "string", "description": "month_review: YYYY-MM; default this month."},
                "items": {"type": "array", "items": {"type": "string"},
                          "description": "dashboard_set: up to 6 tracker names, or water/sleep/mood/steps/spending/habits."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"tracker_charts"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    tracker = args.get("tracker") or ""
    days = int(args.get("days") or 0)
    if action == "year_pixels":
        return year_pixels(settings, tracker)
    if action == "compare":
        return compare(settings, tracker, args.get("period") or "week")
    if action == "correlate":
        return correlate(settings, tracker, args.get("other") or "", days)
    if action == "month_review":
        return month_review(settings, args.get("month") or "")
    if action == "dashboard_set":
        return dashboard_set(settings, args.get("items") or [])
    if action == "dashboard":
        return dashboard(settings)
    return chart(settings, tracker, days)
