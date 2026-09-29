"""Shared bits for the personal-assistant abilities: assistant.json in the memory folder, dates and pop-up cards.

assistant.json holds follow-ups, waiting-for, delegated items, decisions, wins, errands, preferences, countdowns,
things to remember, today's energy and focus mode. It never leaves this PC. To-dos, reminders, birthdays, people,
promises and the calendar stay with their own abilities, and are only read from here.
"""

import re
from datetime import date, datetime, timedelta

import homestore as hs
import screen
from config import Settings

FILE = "assistant.json"
LISTS = ("items", "decisions", "wins", "errands", "prefs", "countdowns", "forgets", "focuslog")
LIMITS = {"items": 300, "decisions": 300, "wins": 400, "errands": 100, "prefs": 60, "countdowns": 100,
          "forgets": 60, "focuslog": 300}
KINDS = ("followup", "waiting", "delegated")
KIND_NAMES = {"followup": "Follow-ups", "waiting": "Waiting for", "delegated": "Delegated", "commitment": "Promises I made"}
screen.EXTRA_KINDS.update({"assistant-briefing", "assistant-timeline"})


def load(settings: Settings) -> dict:
    data = hs.load(settings, FILE, {})
    for key in LISTS:
        data[key] = [e for e in data.get(key) or [] if isinstance(e, dict)]
    for key in ("focus", "energy"):
        data[key] = data[key] if isinstance(data.get(key), dict) else {}
    return data


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def put(data: dict, key: str, entry: dict) -> dict:
    data[key] = (data[key] + [entry])[-LIMITS[key]:]
    return entry


def words(text) -> list[str]:
    return re.findall(r"[a-z0-9']+", str(text or "").lower())


def matches(entry_text: str, wanted: str) -> bool:
    want = words(wanted)
    return bool(want) and all(w in str(entry_text).lower() for w in want)


def upcoming_day(value, base: date | None = None) -> date:
    """A date, 'today', 'tomorrow' or a weekday name (the next one, never a past one)."""
    base = base or hs.today()
    text = hs.clean(value).lower()
    when = hs.parse_day(text, base)
    return when + timedelta(days=7) if text in hs.WEEKDAYS and when < base else when


def when_words(iso: str, today: date) -> str:
    if not iso:
        return "no date"
    days = (date.fromisoformat(iso) - today).days
    if days < 0:
        return f"overdue by {hs.plural(-days, 'day')}"
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return f"in {days} days" if days < 7 else f"on {hs.spoken(date.fromisoformat(iso))}"


def open_items(data: dict, kind: str | None = None) -> list[dict]:
    return [i for i in data["items"] if not i.get("done") and (kind is None or i.get("kind") == kind)]


def due_items(data: dict, today: date, ahead: int = 0) -> list[dict]:
    limit = (today + timedelta(days=ahead)).isoformat()
    return sorted((i for i in open_items(data) if i.get("by") and i["by"] <= limit), key=lambda i: i["by"])


def item_line(i: dict, today: date) -> str:
    who = f" ({i['who']})" if i.get("who") else ""
    return f"{i['what']}{who}, {when_words(i['by'], today)}" if i.get("by") else f"{i['what']}{who}"


def promises(settings: Settings) -> list[dict]:
    """Promises the user made to people, read from the people notebook."""
    return [p for p in hs.load(settings, "people-promises.json", []) if isinstance(p, dict)
            and not p.get("done") and p.get("direction", "i_owe") == "i_owe" and p.get("what")]


def _next_yearly(iso: str, today: date) -> date:
    first = date.fromisoformat(iso)
    for year in (today.year, today.year + 1):
        try:
            when = first.replace(year=year)
        except ValueError:
            when = date(year, 2, 28)
        if when >= today:
            return when
    return first


def countdown_date(c: dict, today: date) -> date:
    first = date.fromisoformat(c["date"])
    return _next_yearly(c["date"], today) if c.get("yearly") and first < today else first


def countdown_rows(data: dict, today: date) -> list[tuple[date, dict]]:
    return sorted(((countdown_date(c, today), c) for c in data["countdowns"]), key=lambda r: r[0])


def countdown_soon(data: dict, today: date, days: int = 21) -> list[str]:
    """Anniversaries and renewals worth a mention: the date is close, or a renewal's notice date has come."""
    out = []
    for when, c in countdown_rows(data, today):
        left = (when - today).days
        if left < 0:
            continue
        cost = f", {c['cost']}" if c.get("cost") else ""
        if left <= days:
            out.append(f"{c['label']} {when_words(when.isoformat(), today)}{cost}")
        elif c.get("kind") == "renewal" and left <= int(c.get("notice") or 0):
            out.append(f"{c['label']} renews {when_words(when.isoformat(), today)}{cost}: time to compare deals")
    return out


def nudges(data: dict, today: date, count: int = 2) -> list[str]:
    """A rotating couple of the things the user keeps forgetting, new ones each day."""
    found = [f["text"] for f in data["forgets"] if f.get("text")]
    if not found:
        return []
    start = today.toordinal() * count % len(found)
    return [found[(start + n) % len(found)] for n in range(min(count, len(found)))]


def line(text: str, say: str = "") -> dict | str:
    return {"text": text, "say": say} if say else text


def section(title: str, lines: list, tone: str = "") -> dict:
    return {"title": title, "lines": lines, "tone": tone}


def panel(title: str, card_id: str, headline: str, sections: list[dict], buttons=None) -> dict:
    """An assistant-briefing pop-up: a headline and titled sections of lines (a line may carry a say)."""
    return screen.card("assistant-briefing", title, card_id, buttons=buttons,
                       data={"headline": headline, "sections": [s for s in sections if s["lines"]]})


def need_date(value, what: str = "date") -> date:
    text = hs.need(value, what, 12)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"Give the {what} as YYYY-MM-DD.") from None


def stamp(when: datetime) -> str:
    return when.strftime("%Y-%m-%d %H:%M")
