"""Shared bits for the creator calendar and stats abilities: one JSON file (creatorstats.json) in the memory folder.

Accounts, planned and posted videos, the numbers the user types in (views, likes...), hook tests and eligibility
notes all live there. Nothing is fetched from or sent to any platform; every number is entered by the user.
"""

import re
from datetime import date, timedelta

import homestore as hs
from config import Settings

FILE = "creatorstats.json"
CHECKPOINTS = ["1h", "24h", "7d"]
METRICS = ["views", "likes", "comments", "shares", "saves", "watch", "follows"]
MILESTONES = [1_000, 10_000, 100_000, 1_000_000]
DEFAULT_SLOTS = ["07:30", "12:30", "19:30"]
DEFAULT_TIMES = {
    "weekdays": ["07:00-08:00 before work or school", "12:00-13:00 lunch break", "18:00-21:00 evening scroll"],
    "weekends": ["09:00-11:00 lazy morning", "19:00-21:00 Saturday and Sunday evening"],
}
MAX_ACCOUNTS = 12
MAX_POSTS = 2000
MAX_HOOKS = 200
GUIDANCE = "General UK guidance only, not a promise; your own numbers beat it."


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    out = {"accounts": {}, "posts": [], "hooks": [], "eligibility": [], "best_times": {}, "next_id": 1}
    for key, kind in (("accounts", dict), ("posts", list), ("hooks", list), ("eligibility", list), ("best_times", dict)):
        if isinstance(found.get(key), kind):
            out[key] = found[key]
    if isinstance(found.get("next_id"), int):
        out["next_id"] = found["next_id"]
    return out


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def blank_account(platform: str, niche: str, goal: int) -> dict:
    return {"platform": platform, "niche": niche, "goal_followers": goal, "goal_date": "", "followers": [],
            "slots": list(DEFAULT_SLOTS), "rpm": 0}


def account(data: dict, name) -> tuple[str, dict]:
    """(key, account): the one named, else the only account."""
    accounts = data["accounts"]
    if not accounts:
        raise ValueError("You haven't added an account yet. Say the name, platform and niche, like: add account lowkey.lore on TikTok.")
    if not hs.clean(name):
        if len(accounts) == 1:
            key = next(iter(accounts))
            return key, accounts[key]
        raise ValueError("Which account? You have " + ", ".join(accounts) + ".")
    key = hs.find(accounts, name)
    if key is None:
        raise ValueError(f"I don't have an account called {hs.clean(name)}.")
    return key, accounts[key]


def accounts_for(data: dict, name) -> list[str]:
    """Every account, or just the one named."""
    if hs.clean(name):
        return [account(data, name)[0]]
    return list(data["accounts"])


def post(data: dict, ref, acct=None) -> dict:
    """A post by number ("3") or part of its title, optionally within one account."""
    text = hs.clean(ref, 100)
    pool = [p for p in data["posts"] if not hs.clean(acct) or p["account"].lower() == hs.clean(acct).lower()]
    if not text:
        raise ValueError("Which video? Give its number or part of its title.")
    if text.lstrip("#").isdigit():
        found = [p for p in pool if p["id"] == int(text.lstrip("#"))]
    else:
        found = [p for p in pool if text.lower() == p["title"].lower()] or [p for p in pool if text.lower() in p["title"].lower()]
    if not found:
        raise ValueError(f"I can't find a video called {text}.")
    if len(found) > 1:
        raise ValueError("That matches more than one video: " + ", ".join(f"#{p['id']} {p['title']}" for p in found[:5]) + ".")
    return found[0]


def new_post(data: dict, acct: str, title: str, **extra) -> dict:
    if len(data["posts"]) >= MAX_POSTS:
        raise ValueError("That's a lot of videos; export your stats and tidy up first.")
    entry = {"id": data["next_id"], "account": acct, "title": title, "theme": "", "hook": "", "length": 0,
             "planned_date": "", "planned_time": "", "posted_date": "", "posted_time": "", "stats": {}}
    entry.update({k: v for k, v in extra.items() if v not in (None, "")})
    data["next_id"] += 1
    data["posts"].append(entry)
    return entry


def is_posted(p: dict) -> bool:
    return bool(p["posted_date"])


def latest(p: dict) -> dict:
    """The newest checkpoint's numbers (7d, else 24h, else 1h)."""
    for cp in reversed(CHECKPOINTS):
        if p["stats"].get(cp):
            return p["stats"][cp]
    return {}


def rates(m: dict) -> dict:
    views = m.get("views") or 0
    if not views:
        return {"engagement": 0.0, "share": 0.0, "save": 0.0, "like": 0.0, "comment": 0.0}

    def pct(n):
        return round((n or 0) / views * 100, 2)

    total = sum(m.get(k) or 0 for k in ("likes", "comments", "shares", "saves"))
    return {"engagement": pct(total), "share": pct(m.get("shares")), "save": pct(m.get("saves")),
            "like": pct(m.get("likes")), "comment": pct(m.get("comments"))}


def views_of(p: dict) -> int:
    return int(latest(p).get("views") or 0)


def parse_time(value) -> str:
    """'19:30', '7:30pm', '7pm' or '19' as HH:MM, or ValueError."""
    text = hs.clean(value).lower().replace(".", ":")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not m:
        raise ValueError("Give the time like 19:30 or 7:30pm.")
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    if m.group(3) == "pm" and hour < 12:
        hour += 12
    if m.group(3) == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        raise ValueError("That time doesn't look right.")
    return f"{hour:02d}:{minute:02d}"


def count(n: float) -> str:
    n = float(n or 0)
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if abs(n) >= 10_000:
        return f"{n / 1000:.0f}k"
    if abs(n) >= 1_000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return f"{n:g}"


def gbp(n: float) -> str:
    return f"£{n:,.2f}"


def current_followers(acct: dict) -> int | None:
    return acct["followers"][-1]["count"] if acct["followers"] else None


def daily_growth(acct: dict, today: date, window: int = 28) -> float | None:
    """Followers gained per day from the recent log entries, or None with fewer than two days of numbers."""
    log = sorted(acct["followers"], key=lambda e: e["date"])
    recent = [e for e in log if (today - date.fromisoformat(e["date"])).days <= window]
    if len(recent) < 2:
        recent = log[-2:]
    if len(recent) < 2:
        return None
    days = (date.fromisoformat(recent[-1]["date"]) - date.fromisoformat(recent[0]["date"])).days
    return (recent[-1]["count"] - recent[0]["count"]) / days if days > 0 else None


def month_start(text, today: date) -> date:
    """First day of a month from 'YYYY-MM', 'this month', 'next month' or 'last month'."""
    t = hs.clean(text).lower()
    if not t or t in ("this month", "today"):
        return today.replace(day=1)
    if t == "next month":
        return (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    if t == "last month":
        return (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    try:
        return date.fromisoformat(t[:7] + "-01")
    except ValueError:
        raise ValueError("Give the month as YYYY-MM, like 2026-10.") from None


def button(label: str, say: str) -> dict:
    return {"label": label, "say": say}


def whole(value, what: str, high: int = 10_000_000_000) -> int:
    return int(hs.number(value, what, 0, high))


def slot_index(acct: dict, time: str) -> int:
    """Which of the account's posting slots a time belongs to (the nearest one)."""
    slots = acct["slots"] or DEFAULT_SLOTS
    if not time:
        return 0

    def minutes(t):
        return int(t[:2]) * 60 + int(t[3:5])

    return min(range(len(slots)), key=lambda i: abs(minutes(slots[i]) - minutes(time)))


def safe_cell(value) -> str:
    text = str(value if value is not None else "")
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text
