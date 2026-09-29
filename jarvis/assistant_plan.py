"""Assistant helpers for planning: which job to do next (by priority, time and energy), a time-blocked day and
meeting preparation. Read-only: it looks at the to-do list, reminders, follow-ups, promises, people, past meeting
notes and the calendar, and changes nothing.
"""

import re
from datetime import timedelta

import assistant_store as st
import homestore as hs
import people_store as ps
import routines_brief
import screen
import todo
import worktools_store as ws
from config import Settings

URGENT = ("urgent", "asap", "today", "!", "overdue", "deadline", "now")
IMPORTANT = ("important", "must", "bill", "pay", "doctor", "tax", "renew")
QUICK = ("call", "phone", "text", "email", "reply", "pay", "book", "order", "post", "quick", "ring")
DEEP = ("write", "plan", "report", "review", "study", "draft", "essay", "design", "build", "research")
TIME_OF_DAY = re.compile(r"^(\d{1,2}):(\d{2})$")
ENERGY = ("low", "medium", "high")


def energy_today(data: dict, today) -> str:
    saved = data["energy"]
    return saved.get("level", "medium") if saved.get("date") == today.isoformat() else "medium"


def _rate(text: str, energy: str, minutes: int) -> tuple[int, list[str]]:
    low, score, why = text.lower(), 0, []
    quick, deep = any(w in low for w in QUICK), any(w in low for w in DEEP)
    for words, points, label in ((URGENT, 3, "sounds urgent"), (IMPORTANT, 2, "matters")):
        if any(w in low for w in words):
            score += points
            why.append(label)
    if energy == "low" and quick or energy == "high" and deep:
        score += 2
        why.append(f"suits {energy} energy")
    elif energy == "low" and deep:
        score -= 2
    if minutes and minutes <= 15 and quick:
        score += 3
        why.append(f"quick, and you have {minutes} minutes")
    elif minutes and minutes <= 15 and deep:
        score -= 3
    return score, why


def ranked(settings: Settings, data: dict, today, energy: str = "medium", minutes: int = 0) -> list[dict]:
    """Everything that could be done now, best first: {text, source, score, why}."""
    found = []
    for job in todo.open_items(settings):
        score, why = _rate(job, energy, minutes)
        found.append({"text": job, "source": "todo", "score": score, "why": why})
    for i in st.due_items(data, today):
        late = i["by"] < today.isoformat()
        found.append({"text": f"{'Chase' if i['kind'] == 'followup' else 'Check on'}: {i['what']}"
                              + (f" ({i['who']})" if i["who"] else ""), "source": "chase", "score": 6 if late else 4,
                      "why": ["overdue" if late else "due today"]})
    for p in st.promises(settings):
        if p.get("due") and p["due"] <= (today + timedelta(days=1)).isoformat():
            found.append({"text": f"Keep your promise to {p['person']}: {p['what']}", "source": "promise", "score": 5,
                          "why": [f"you promised, {st.when_words(p['due'], today)}"]})
    return sorted(found, key=lambda f: -f["score"])


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _minutes(value, default: int) -> int:
    m = TIME_OF_DAY.match(str(value or "").strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else default


def earliest(prefs: list[str], text: str) -> int:
    """The earliest minute of the day this job may go in, from preferences like 'no calls before 10'."""
    if not any(w in text.lower() for w in ("call", "phone", "ring", "meeting")):
        return 0
    for p in prefs:
        m = re.search(r"(call|phone|meeting).*?before (\d{1,2})(?::(\d{2}))?", p.lower())
        if m:
            return int(m.group(2)) * 60 + int(m.group(3) or 0)
    return 0


async def block_day(settings: Settings, http, args: dict) -> screen.Shown:
    now = hs.now()
    day = hs.parse_day(args.get("day") or "today", now.date())
    start = now.replace(year=day.year, month=day.month, day=day.day, hour=0, minute=0, second=0, microsecond=0)
    first, last = _minutes(args.get("start"), 9 * 60), _minutes(args.get("end"), 17 * 60 + 30)
    if day == now.date():
        first = max(first, (now.hour * 60 + now.minute + 14) // 15 * 15)
    data = st.load(settings)
    events = await routines_brief._events(http, settings, start, 1)
    fixed = [(e["start"].hour * 60 + e["start"].minute, e["start"].hour * 60 + e["start"].minute + 60, e["title"], "event")
             for e in events or [] if not e["all_day"]]
    fixed += [(at.hour * 60 + at.minute, at.hour * 60 + at.minute + 15, text, "reminder")
              for at, text in routines_brief.reminders_between(settings, start, start + timedelta(days=1))]
    if not any(f[0] < 13 * 60 and f[1] > 12 * 60 + 30 for f in fixed) and first < 13 * 60 - 15 and last > 13 * 60:
        fixed.append((12 * 60 + 30, 13 * 60, "Lunch", "break"))
    fixed = sorted(f for f in fixed if first <= f[0] < last)
    prefs = [p["text"] for p in data["prefs"]]
    queue = ranked(settings, data, day, energy_today(data, day))[:8]
    blocks, cursor = [], first

    def fill(until: int) -> None:
        nonlocal cursor
        while until - cursor >= 30 and queue:
            task = next((t for t in queue if earliest(prefs, t["text"]) <= cursor), None)
            if task is None:
                cursor += 30
                continue
            queue.remove(task)
            length = 60 if until - cursor >= 60 and any(w in task["text"].lower() for w in DEEP) else 30
            blocks.append({"start": _clock(cursor), "end": _clock(cursor + length), "label": task["text"], "kind": "task"})
            cursor += length

    for begin, end, label, kind in fixed:
        fill(begin)
        blocks.append({"start": _clock(begin), "end": _clock(end), "label": label, "kind": kind})
        cursor = max(cursor, end)
    fill(last)
    if not blocks:
        raise ValueError("There's nothing to plan into that time.")
    tasks = sum(b["kind"] == "task" for b in blocks)
    note = "Meetings are drawn as an hour long." + (" Preferences applied." if prefs else "")
    card = screen.card("assistant-timeline", f"Plan for {hs.spoken(day)}", "assistant-blocks",
                       data={"from": _clock(first), "to": _clock(last), "blocks": blocks, "note": note},
                       buttons=[{"label": "What next?", "say": "What should I do next?"}])
    lines = "; ".join(f"{b['start']} {b['label']}" for b in blocks)
    return screen.Shown(f"Planned {hs.plural(len(blocks), 'block')} with {hs.plural(tasks, 'task')} (on screen): {lines}", card)


def _people_in(book: dict, text: str) -> list[str]:
    low = text.lower()
    return [k for k in book if k.lower() in low or (k.split()[0].lower() in st.words(low) and len(k.split()[0]) > 2)]


def _person_lines(settings: Settings, k: str, p: dict, today) -> list[str]:
    out = [f"{k}: {p['how']}" if p.get("how") else k, f"  Last in touch {ps.ago(ps.last_contact(p), today)}"]
    out += [f"  Likes {', '.join(p['likes'][:3])}"] if p.get("likes") else []
    out += [f"  Note: {p['notes'][-1]['text']}"] if p.get("notes") else []
    return out


async def prepare(settings: Settings, http, title) -> screen.Shown:
    now = hs.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    events = await routines_brief._events(http, settings, start, 3)
    if events is None:
        raise ValueError("No calendar is connected, so I can't tell what your next meeting is.")
    want = hs.clean(title).lower()
    timed = [e for e in events if not e["all_day"] and (e["start"] > now or want)]
    event = next((e for e in timed if want in e["title"].lower()), None)
    if event is None:
        raise ValueError("I can't find a meeting to prepare for in the next few days.")
    data, today = st.load(settings), now.date()
    book = ps.book(settings)
    names = _people_in(book, f"{event['title']} {event['where']}")
    topic = [w for w in st.words(event["title"]) if len(w) > 3 and w not in ("meeting", "call", "with", "catch")]
    past = [m for m in ws.meetings(settings)["meetings"] if any(w in m["title"].lower() for w in topic)][-1:]
    chase = [st.item_line(i, today) for i in st.open_items(data)
             if any(n.split()[0].lower() in f"{i['who']} {i['what']}".lower() for n in names)]
    chase += [f"You promised {p['person']}: {p['what']}" for p in st.promises(settings) if p["person"] in names]
    decisions = [f"{d['date']}: {d['text']}" for d in data["decisions"] if any(w in d["text"].lower() for w in topic)][-3:]
    minutes = round((event["start"] - now).total_seconds() / 60)
    when = f"{event['start']:%H:%M}" + (f" at {event['where']}" if event["where"] else "")
    sections = [st.section("The meeting", [f"{event['title']}, {when}", f"Starts in {hs.plural(max(minutes, 0), 'minute')}"]),
                st.section("Who", [ln for k in names for ln in _person_lines(settings, k, book[k], today)]),
                st.section("Last time", [f"{m['date']}: {m['notes'][:160]}" if m.get("notes") else m["date"] for m in past]
                           + [f"Open: {a['text']}" for m in past for a in m["actions"] if not a.get("done")]),
                st.section("Open with them", chase, "alert"), st.section("Decisions so far", decisions)]
    card = st.panel(f"Prepare: {event['title']}", "assistant-prep", f"{event['start']:%A %H:%M}", sections)
    said = f"Next meeting: {event['title']} at {event['start']:%H:%M}, in {hs.plural(max(minutes, 0), 'minute')}."
    return screen.Shown(said + f" Prep on screen: {len(names)} people, {len(chase)} open items.", card)
