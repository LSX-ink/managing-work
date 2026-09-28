"""Keeping in touch: how often to contact someone, a log of calls and visits with what you talked about,
who's overdue, and a weekly social summary.

Saved only in the people-*.json files in the memory folder; nothing is sent anywhere.
"""

from datetime import date, timedelta

import homestore as hs
import people_store as ps
import screen
from config import Settings

WAYS = ("call", "text", "message", "video call", "visit", "email", "letter", "met up")


def every(settings: Settings, name, days) -> str:
    found = ps.book(settings)
    k = ps.person(found, name)
    days = int(hs.number(days if days is not None else 0, "number of days", 0, 3650))
    found[k]["every"] = days
    ps.save(settings, found)
    if not days:
        return f"Stopped the keep-in-touch goal for {k}."
    late = ps.overdue_days(found[k], hs.today())
    return f"I'll aim for you to be in touch with {k} every {hs.plural(days, 'day')}." + \
        (" You're due to get in touch now." if late is not None else "")


def contacted(settings: Settings, name, how=None, when=None, topics=None, text=None) -> str:
    found = ps.book(settings)
    k = ps.person(found, name)
    day = hs.parse_day(when)
    if day > hs.today():
        raise ValueError("That's in the future; tell me once you've been in touch.")
    how = how if how in WAYS else "call"
    entry = {"date": day.isoformat(), "how": how, "topics": ps.words(topics, 12, 80), "note": hs.clean(text, 300)}
    found[k]["contacts"] = sorted(found[k]["contacts"] + [entry], key=lambda c: c["date"])[-ps.MAX_LOG:]
    ps.save(settings, found)
    nxt = f" Next catch-up due in {hs.plural(found[k]['every'], 'day')}." if found[k].get("every") and \
        day == ps.last_contact(found[k]) else ""
    return f"Logged a {how} with {k} {ps.ago(day, hs.today())}.{nxt}"


def overdue(settings: Settings) -> screen.Shown | str:
    found = ps.book(settings)
    today = hs.today()
    late = sorted(((ps.overdue_days(p, today), k) for k, p in found.items()
                   if ps.overdue_days(p, today) is not None), key=lambda x: (-x[0], x[1].lower()))
    if not late:
        goals = sum(bool(p.get("every")) for p in found.values())
        return "You're up to date with everyone." if goals else \
            "No keep-in-touch goals yet. Say something like 'I want to call Mum every 7 days'."
    items = [{"label": f"{k} - {'due today' if n == 0 else hs.plural(n, 'day') + ' overdue'}, last in touch "
                       f"{ps.ago(ps.last_contact(found[k]), today)}", "say": f"I've just been in touch with {k}."}
             for n, k in late]
    card = screen.card("list", "Time to get in touch", "people-overdue", items=items, checks=True)
    names = ", ".join(k for _, k in late[:5])
    return screen.Shown(f"{hs.plural(len(late), 'person', 'people')} to get in touch with: {names}. "
                        "Tick them off when you have.", card)


def conversations(settings: Settings, name) -> screen.Shown | str:
    found = ps.book(settings)
    k = ps.person(found, name)
    log = found[k]["contacts"]
    if not log:
        return f"Nothing logged with {k} yet."
    card = screen.card("table", f"Conversations with {k}", f"people-talks-{k.lower()}",
                       columns=["Date", "How", "Talked about", "Note"],
                       rows=[[ps.short(date.fromisoformat(c["date"])), c.get("how", ""), ", ".join(c.get("topics", [])),
                              c.get("note", "")] for c in reversed(log)])
    topics = log[-1].get("topics")
    about = f", about {', '.join(topics)}" if topics else ""
    return screen.Shown(f"{hs.plural(len(log), 'catch-up')} with {k}; the last was "
                        f"{ps.ago(date.fromisoformat(log[-1]['date']), hs.today())}{about}.", card)


def _upcoming(settings: Settings, found: dict, today: date, days: int = 14) -> list[tuple[date, str]]:
    soon = []
    saved = hs.load(settings, "birthdays.json", {})
    for name in saved:
        value = ps.birthday(settings, name)
        if value:
            when, _ = ps.next_date(value, today)
            soon.append((when, f"{name}'s birthday"))
    for k, p in found.items():
        for label, value in p.get("dates", {}).items():
            when, _ = ps.next_date(value, today)
            soon.append((when, f"{k}: {label}"))
    return sorted(x for x in soon if (x[0] - today).days <= days)


def _some(bits: list[str], sep: str) -> str:
    return f" ({sep.join(bits[:6])})" if bits else ""


def week(settings: Settings) -> screen.Shown:
    found = ps.book(settings)
    today = hs.today()
    start = today - timedelta(days=6)
    seen = sorted((c["date"], k, c.get("how", "")) for k, p in found.items() for c in p.get("contacts", [])
                  if c.get("date", "") >= start.isoformat())
    late = sorted(k for k, p in found.items() if ps.overdue_days(p, today) is not None)
    soon = _upcoming(settings, found, today)
    thanks = [t for t in ps.entries(settings, ps.THANKS) if not t.get("sent")]
    promises = [p for p in ps.entries(settings, ps.PROMISES) if not p.get("done")]
    due = [p for p in promises if p.get("due") and p["due"] <= (today + timedelta(days=7)).isoformat()]
    parts = [f"In touch this week ({hs.plural(len(seen), 'time')}):"]
    parts += [f"- {k}, {how}, {ps.ago(date.fromisoformat(d), today)}" for d, k, how in seen] or ["- nobody logged yet"]
    parts += ["", "Due a catch-up: " + (", ".join(late) if late else "nobody")]
    parts += ["", "Coming up in the next two weeks:"]
    parts += [f"- {what}, {ps.until(when, today)}" for when, what in soon] or ["- nothing saved"]
    parts += ["", f"Thank-yous to send: {len(thanks)}" + _some([t["person"] for t in thanks], ", ")]
    parts += [f"Promises due this week: {len(due)}" + _some([f"{p['person']}: {p['what']}" for p in due], "; ")]
    card = screen.card("text", "Your week with people", "people-week", text="\n".join(parts), buttons=[
        {"label": "Who's overdue", "say": "Who am I overdue to get in touch with?"},
        {"label": "Thank-yous", "say": "Show my thank-you list."},
        {"label": "Promises", "say": "Show the promises and favours I owe."}])
    spoken = f"This week you've been in touch {hs.plural(len(seen), 'time')}"
    spoken += f", {len(late)} {'person is' if len(late) == 1 else 'people are'} due a catch-up" if late else ""
    spoken += f", and {soon[0][1]} is {ps.until(soon[0][0], today)}." if soon else "."
    return screen.Shown(spoken, card)


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "people_keep_in_touch",
        "description": "Keeping in touch with friends and family. every (name, days: 'call Mum every 7 days'; 0 "
                       "stops), contacted logs a call, visit or message ('I called Mum', how, optional date, topics "
                       "talked about, text note), overdue (who I haven't been in touch with lately; tick-list pop-up), "
                       "conversations (log of catch-ups with one person, dates and topics), week (weekly social "
                       "summary pop-up: who you saw, who's due, birthdays and dates coming up, thank-yous, promises).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["every", "contacted", "overdue", "conversations", "week"]},
                "name": {"type": "string", "description": "The person."},
                "days": {"type": "integer"},
                "how": {"type": "string", "enum": list(WAYS)},
                "date": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'yesterday'."},
                "topics": {"type": "array", "items": text},
                "text": text,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"people_keep_in_touch"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    who = a("name")
    actions = {
        "every": lambda: every(settings, who, a("days")),
        "contacted": lambda: contacted(settings, who, a("how"), a("date"), a("topics"), a("text")),
        "overdue": lambda: overdue(settings),
        "conversations": lambda: conversations(settings, who),
        "week": lambda: week(settings),
    }
    if a("action") not in actions:
        raise ValueError("Unknown keep-in-touch action.")
    return actions[a("action")]()
