"""Shared bits for "track anything": the user's own trackers, their daily values, goals, stats and the other logs
(water, sleep, mood, steps, spending, habits) read as daily series so they can sit on the dashboard.

Saved in trackers-*.json files in the memory folder on this PC and nowhere else.
"""

import difflib
import json
import re
from datetime import date, timedelta

import habits
import homewellbeing
import memory
import money
from config import Settings

TYPES = {"number": "", "yes_no": "", "rating": "out of 5", "count": "", "duration": "min", "text": ""}
ADD_UP = {"number", "count", "duration"}
MAX_TRACKERS = 40
KEEP_DAYS = 1100
BUILTIN = ("water", "sleep", "mood", "steps", "spending", "habits")


def today() -> date:
    return date.today()


def load(settings: Settings, section: str, default):
    try:
        found = json.loads((memory.root(settings) / f"trackers-{section}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return found if isinstance(found, type(default)) else default


def save(settings: Settings, section: str, data) -> None:
    p = memory.root(settings) / f"trackers-{section}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)


def trackers(settings: Settings) -> dict:
    data = load(settings, "data", {})
    return {"trackers": {k: v for k, v in (data.get("trackers") or {}).items() if isinstance(v, dict)},
            "values": {k: v for k, v in (data.get("values") or {}).items() if isinstance(v, dict)},
            "notes": {k: v for k, v in (data.get("notes") or {}).items() if isinstance(v, dict)}}


def save_trackers(settings: Settings, data: dict) -> None:
    cutoff = (today() - timedelta(days=KEEP_DAYS)).isoformat()
    for key in ("values", "notes"):
        data[key] = {n: {d: v for d, v in days.items() if d >= cutoff} for n, days in data[key].items()}
    save(settings, "data", data)


def clean(value, limit: int = 40) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def stem(word: str) -> str:
    """'My push-ups counter' -> 'pushup': lower case, no spaces or plural, so spoken names match."""
    word = re.sub(r"[^a-z0-9]+", " ", word.lower()).strip()
    word = re.sub(r"^(my|the) ", "", word)
    word = re.sub(r" (tracker|counter|log)$", "", word).replace(" ", "")
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def find(names, wanted: str) -> str | None:
    """The tracker a spoken name means: exact, then singular/plural, then contained, then a close spelling."""
    names = list(names)
    want = stem(clean(wanted))
    if not want:
        return None
    for match in (lambda n: stem(n) == want, lambda n: want in stem(n) or stem(n) in want):
        found = [n for n in names if match(n)]
        if len(found) == 1:
            return found[0]
    close = difflib.get_close_matches(want, [stem(n) for n in names], n=1, cutoff=0.75)
    return next((n for n in names if stem(n) == close[0]), None) if close else None


def need(data: dict, wanted: str) -> str:
    name = find(data["trackers"], wanted)
    if name is None:
        have = ", ".join(data["trackers"]) or "none yet"
        raise ValueError(f"There's no tracker called {clean(wanted) or 'that'}. Your trackers: {have}.")
    return name


def unit_of(info: dict) -> str:
    return info.get("unit") or TYPES.get(info.get("type"), "")


def fmt(value, info: dict) -> str:
    if value is None:
        return "-"
    kind = info.get("type")
    if kind == "yes_no":
        return "yes" if value else "no"
    if kind == "duration":
        return f"{int(value) // 60} h {int(value) % 60} min" if value >= 60 else f"{value:g} min"
    unit = unit_of(info)
    return f"{round(value, 2):g}{' ' + unit if unit else ''}"


def met(value, info: dict) -> bool:
    goal = info.get("goal")
    if value is None or goal is None:
        return False
    return value <= goal if info.get("goal_type") == "at_most" else value >= goal


def days_back(end: date, n: int) -> list[date]:
    return [end - timedelta(days=i) for i in range(n - 1, -1, -1)]


def goal_streak(values: dict, info: dict, end: date) -> int:
    day = end if met(values.get(end.isoformat()), info) else end - timedelta(days=1)
    count = 0
    while met(values.get(day.isoformat()), info):
        count += 1
        day -= timedelta(days=1)
    return count


def stats(values: dict, info: dict, days: list[date]) -> dict:
    got = [values[d.isoformat()] for d in days if d.isoformat() in values]
    out = {"logged": len(got), "total": sum(got), "average": sum(got) / len(got) if got else None,
           "min": min(got) if got else None, "max": max(got) if got else None}
    if info.get("goal") is not None:
        out["goal_days"] = sum(met(values.get(d.isoformat()), info) for d in days)
        out["streak"] = goal_streak(values, info, days[-1])
    return out


# ---- The other logs, read as daily series ----------------------------------------------------

def builtin(settings: Settings, name: str) -> tuple[dict, dict]:
    """(info, {iso day: value}) for one of the other logs, read from their own modules."""
    if name in ("water", "sleep"):
        data = homewellbeing.load(settings)
        info = {"type": "number", "unit": "glasses" if name == "water" else "h",
                "goal": data["goal"] if name == "water" else None}
        return info, dict(data[name])
    if name == "mood":
        return {"type": "rating"}, {m["date"]: m["mood"] for m in homewellbeing.load(settings)["mood"]
                                    if isinstance(m.get("mood"), (int, float)) and m.get("date")}
    if name == "steps":
        found = memory.root(settings) / "growth-steps.json"
        try:
            days = json.loads(found.read_text(encoding="utf-8")).get("days") or {}
        except (OSError, ValueError, AttributeError):
            days = {}
        return {"type": "count", "unit": "steps"}, {d: v.get("steps", 0) for d, v in days.items() if isinstance(v, dict)}
    if name == "spending":
        out: dict[str, float] = {}
        for s in money.load(settings)["spending"]:
            out[s.get("date", "")] = round(out.get(s.get("date", ""), 0) + float(s.get("amount") or 0), 2)
        return {"type": "number", "unit": settings.currency}, out
    if name == "habits":
        out = {}
        for days in habits.load(settings).values():
            for d in days:
                out[d] = out.get(d, 0) + 1
        return {"type": "count", "unit": "habits done"}, out
    raise ValueError(f"I can't read {name}.")


def series(settings: Settings, wanted: str, data: dict | None = None) -> tuple[str, dict, dict]:
    """(name, info, values) for a tracker or one of the other logs, by a spoken name."""
    data = data or trackers(settings)
    name = find(data["trackers"], wanted)
    if name:
        return name, data["trackers"][name], data["values"].get(name, {})
    other = find(BUILTIN, wanted)
    if other:
        info, values = builtin(settings, other)
        return other, info, values
    have = ", ".join([*data["trackers"], *BUILTIN])
    raise ValueError(f"There's no tracker called {clean(wanted) or 'that'}. You can use: {have}.")
