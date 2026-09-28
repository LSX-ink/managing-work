"""Kids' logs: a reading log with certificates, a growth chart, milestones and first times, and a temperature and
medicine log.

The health log is a diary only: Alfred never suggests doses or diagnoses; for worries it points to NHS 111 or the GP.
Everything is in kids-reading.json, kids-growth.json, kids-milestones.json and kids-health.json in the memory folder.
"""

from datetime import date, datetime, timedelta

import homestore as hs
import kids_store as ks
import screen
from config import Settings

READING, GROWTH, MILESTONES, HEALTH = ("kids-reading.json", "kids-growth.json", "kids-milestones.json",
                                       "kids-health.json")
DEFAULT_TARGET = 10
screen.EXTRA_KINDS.add("kids-certificate")
FEVER_C = 38.0
WORRIED = "If you're worried, call NHS 111 or your GP; in an emergency, call 999."
LOGS = {"reading": READING, "growth": GROWTH, "milestone": MILESTONES, "health": HEALTH}


def _short(day: str) -> str:
    d = date.fromisoformat(day[:10])
    return f"{d.day} {d.strftime('%b')}"


# Reading log

def _reader(found: dict, name, create: bool = True) -> tuple[str, dict]:
    k = ks.child(found, name, create)
    rec = found.get(k) if isinstance(found.get(k), dict) else {}
    rec.setdefault("target", DEFAULT_TARGET)
    rec.setdefault("log", [])
    found[k] = rec
    return k, rec


def _finished(rec: dict) -> list[dict]:
    return [e for e in rec["log"] if e.get("finished")]


def reading_log(settings: Settings, name, book, minutes, finished, when, target) -> str | screen.Shown:
    found = ks.load(settings, READING)
    k, rec = _reader(found, name)
    said = []
    if target:
        rec["target"] = int(hs.number(target, "number of books", 1, 200))
        said.append(f"{k}'s certificate comes every {hs.plural(rec['target'], 'book')}.")
    if book or minutes or finished:
        mins = int(hs.number(minutes or 0, "minutes", 0, 600))
        title = hs.clean(book, 80)
        if finished and not title:
            raise ValueError("Which book was finished?")
        day = hs.parse_day(when)
        rec["log"] = ks.append(rec["log"], {"date": day.isoformat(), "book": title, "minutes": mins,
                                            "finished": bool(finished)})
        said.append(f"Logged {hs.plural(mins, 'minute')} of reading for {k}" + (f": {title}" if title else "")
                    + (". Finished! That's " + hs.plural(len(_finished(rec)), 'book') if finished else "") + ".")
    if not said:
        raise ValueError("What did they read, and for how long?")
    ks.save(settings, READING, found)
    done = len(_finished(rec))
    if finished and done % rec["target"] == 0:
        return screen.Shown(" ".join(said) + " A reading certificate pops up!", certificate_card(k, rec))
    return " ".join(said)


def certificate_card(k: str, rec: dict) -> dict:
    books = _finished(rec)
    count = len(books) - len(books) % rec["target"]
    data = {"child": k, "books": count, "award": "Super Reader", "date": hs.spoken(hs.today()),
            "titles": [b["book"] for b in books[:count]][-6:]}
    return screen.card("kids-certificate", f"{k}'s reading certificate", f"kids-cert-{k}", data=data)


def certificate(settings: Settings, name) -> str | screen.Shown:
    found = ks.load(settings, READING)
    k, rec = _reader(found, ks.only_child(settings, found, name), create=False)
    done = len(_finished(rec))
    if done < rec["target"]:
        return f"{k} has read {hs.plural(done, 'book')}; {rec['target'] - done} more for a certificate."
    return screen.Shown(f"Here's {k}'s certificate for {hs.plural(done - done % rec['target'], 'book')}!",
                        certificate_card(k, rec))


def reading_show(settings: Settings, name) -> screen.Shown:
    found = ks.load(settings, READING)
    k, rec = _reader(found, ks.only_child(settings, found, name), create=False)
    week = hs.week_start(hs.today()).isoformat()
    minutes = sum(e["minutes"] for e in rec["log"] if e["date"] >= week)
    done = len(_finished(rec))
    togo = rec["target"] - done % rec["target"]
    rows = [[_short(e["date"]), e["book"] or "-", str(e["minutes"]), "yes" if e["finished"] else ""]
            for e in reversed(rec["log"][-30:])]
    buttons = [{"label": "Certificate", "say": f"Show {k}'s reading certificate."}] if done >= rec["target"] else []
    card = screen.card("table", f"{k}'s reading log", f"kids-reading-{k}",
                       columns=["Day", "Book", "Minutes", "Finished"], rows=rows, buttons=buttons,
                       text=f"{minutes} minutes this week. {hs.plural(done, 'book')} finished; "
                            f"{togo} more for the next certificate.")
    return screen.Shown(f"{k} has read {minutes} minutes this week and finished {hs.plural(done, 'book')}.", card)


def reading_this_week(settings: Settings) -> dict:
    week = hs.week_start(hs.today()).isoformat()
    out = {}
    for k, rec in ks.load(settings, READING).items():
        log = [e for e in rec.get("log", []) if e.get("date", "") >= week]
        out[k] = (sum(e.get("minutes", 0) for e in log), sum(bool(e.get("finished")) for e in log))
    return out


# Growth chart

def growth_log(settings: Settings, name, height, weight, when) -> str:
    if height is None and weight is None:
        raise ValueError("What's the height in centimetres or the weight in kilos?")
    found = ks.load(settings, GROWTH)
    k = ks.child(found, name)
    rows = found.get(k) if isinstance(found.get(k), list) else []
    day = hs.parse_day(when).isoformat()
    row = next((r for r in rows if r["date"] == day), None) or {"date": day}
    if height is not None:
        row["height"] = round(hs.number(height, "height in centimetres", 30, 220), 1)
    if weight is not None:
        row["weight"] = round(hs.number(weight, "weight in kilos", 1, 150), 1)
    rows = sorted([r for r in rows if r["date"] != day] + [row], key=lambda r: r["date"])[-ks.MAX_LOG:]
    found[k] = rows
    ks.save(settings, GROWTH, found)
    parts = [f"{row[key]:g} {unit}" for key, unit in (("height", "cm"), ("weight", "kg")) if key in row]
    return f"Logged {k} at {' and '.join(parts)}."


def growth_chart(settings: Settings, name, measure) -> screen.Shown:
    found = ks.load(settings, GROWTH)
    k = ks.only_child(settings, found, name)
    key = "weight" if measure == "weight" else "height"
    unit = " kg" if key == "weight" else " cm"
    rows = [r for r in found[k] if key in r]
    if not rows:
        raise ValueError(f"I haven't got any {key} for {k} yet.")
    change = rows[-1][key] - rows[0][key]
    said = f"{k} is {rows[-1][key]:g}{unit}"
    said += f", {'up' if change >= 0 else 'down'} {abs(change):g}{unit} since {_short(rows[0]['date'])}." \
        if len(rows) > 1 else "."
    other = "height" if key == "weight" else "weight"
    card = screen.card("chart", f"{k}'s {key}", f"kids-growth-{k}", chart={
        "type": "line", "labels": [_short(r["date"]) + " " + r["date"][2:4] for r in rows][-60:],
        "values": [r[key] for r in rows][-60:], "unit": unit.strip()},
        buttons=[{"label": other.title(), "say": f"Show {k}'s {other} chart."}])
    return screen.Shown(said, card)


def latest_height(settings: Settings) -> dict:
    return {k: next((f"{r['height']:g} cm" for r in reversed(rows) if "height" in r), "")
            for k, rows in ks.load(settings, GROWTH).items() if isinstance(rows, list)}


# Milestones and first times

def milestone_add(settings: Settings, name, text, when) -> str:
    found = ks.load(settings, MILESTONES)
    k = ks.child(found, name)
    what = hs.need(text, "milestone", 120)
    day = hs.parse_day(when)
    rows = found.get(k) if isinstance(found.get(k), list) else []
    found[k] = sorted(ks.append(rows, {"date": day.isoformat(), "what": what}), key=lambda r: r["date"])
    ks.save(settings, MILESTONES, found)
    return f"Saved for {k} on {hs.spoken(day)}: {what}."


def milestones(settings: Settings, name) -> screen.Shown:
    found = ks.load(settings, MILESTONES)
    if not found:
        raise ValueError("No milestones saved yet. Say something like 'Mia lost her first tooth today'.")
    kids = [ks.child(found, name, create=False)] if hs.clean(name) else list(found)
    rows = sorted(([r["date"], k, r["what"]] for k in kids for r in found[k]), reverse=True)
    rows = [[f"{_short(d)} {d[:4]}", k, w] for d, k, w in rows]
    title = f"{kids[0]}'s milestones" if len(kids) == 1 else "Milestones and first times"
    card = screen.card("table", title, f"kids-milestones-{'-'.join(kids)}", columns=["Date", "Child", "Milestone"],
                       rows=rows)
    return screen.Shown(f"{hs.plural(len(rows), 'milestone')} on the screen.", card)


def milestones_this_week(settings: Settings) -> dict:
    week = hs.week_start(hs.today()).isoformat()
    return {k: [r["what"] for r in rows if r.get("date", "") >= week]
            for k, rows in ks.load(settings, MILESTONES).items() if isinstance(rows, list)}


# Temperature and medicine log

def health_log(settings: Settings, name, temperature, medicine, amount, note) -> str:
    if temperature is None and not hs.clean(medicine) and not hs.clean(note):
        raise ValueError("What's the temperature, or which medicine was given?")
    found = ks.load(settings, HEALTH)
    k = ks.child(found, name)
    rows = found.get(k) if isinstance(found.get(k), list) else []
    now = hs.now()
    entry = {"time": now.isoformat(timespec="minutes")}
    said = []
    if temperature is not None:
        entry["temp"] = round(hs.number(temperature, "temperature in °C", 34, 43), 1)
        said.append(f"{entry['temp']:g}°C")
    before = next((r for r in reversed(rows) if r.get("medicine")), None)
    if hs.clean(medicine):
        entry["medicine"] = hs.clean(medicine, 60)
        entry["amount"] = hs.clean(amount, 40)
        said.append(entry["medicine"] + (f" ({entry['amount']})" if entry["amount"] else "") + " given")
    if hs.clean(note):
        entry["note"] = hs.clean(note, 120)
    found[k] = ks.append(rows, entry)
    ks.save(settings, HEALTH, found)
    out = f"Logged for {k} at {now.strftime('%H:%M')}: {', '.join(said) or entry.get('note', '')}."
    if entry.get("medicine") and before:
        out += f" The last medicine before that was {before['medicine']} at {_when(before['time'], now)}."
    if entry.get("temp", 0) >= FEVER_C:
        out += f" That's a high temperature. {WORRIED}"
    return out


def _when(stamp: str, now: datetime) -> str:
    t = datetime.fromisoformat(stamp)
    return t.strftime("%H:%M") + ("" if t.date() == now.date() else f" on {t.strftime('%a')} {t.day}")


def health_show(settings: Settings, name) -> screen.Shown:
    found = ks.load(settings, HEALTH)
    k = ks.only_child(settings, found, name)
    since = (hs.now() - timedelta(days=3)).isoformat(timespec="minutes")
    rows = [r for r in found[k] if r["time"] >= since]
    if not rows:
        return screen.Shown(f"Nothing logged for {k} in the last three days.", screen.card(
            "text", f"{k}'s temperature and medicine", f"kids-health-{k}", text=f"Nothing logged in 3 days. {WORRIED}"))
    table = [[_when(r["time"], hs.now()), f"{r['temp']:g}°C" if "temp" in r else "",
              (r.get("medicine", "") + (f" ({r['amount']})" if r.get("amount") else "")), r.get("note", "")]
             for r in reversed(rows)]
    last_med = next((r for r in reversed(rows) if r.get("medicine")), None)
    said = f"{hs.plural(len(rows), 'entry', 'entries')} for {k} in the last three days" + \
        (f"; the last medicine was {last_med['medicine']} at {_when(last_med['time'], hs.now())}." if last_med else ".")
    card = screen.card("table", f"{k}'s temperature and medicine", f"kids-health-{k}",
                       columns=["When", "Temperature", "Medicine", "Note"], rows=table,
                       text=f"A log only, not advice. {WORRIED}")
    return screen.Shown(said, card)


# Mistakes

def undo_last(settings: Settings, name, which, confirmed: bool) -> str:
    if which not in LOGS:
        raise ValueError("Which log: reading, growth, milestone or health?")
    found = ks.load(settings, LOGS[which])
    k = ks.only_child(settings, found, name)
    rows = found[k]["log"] if which == "reading" else found[k]
    if not rows:
        raise ValueError(f"There's nothing in {k}'s {which} log.")
    last = rows[-1]
    what = ", ".join(f"{v}" for key, v in last.items() if key not in ("finished",) and v not in ("", None))
    if not confirmed:
        return f"The last {which} entry for {k} is: {what}. Ask the user to confirm removing it, then call again " \
               "with confirmed true."
    rows.pop()
    ks.save(settings, LOGS[which], found)
    return f"Removed {k}'s last {which} entry ({what})."


# The tool

ACTIONS = ("reading_log", "reading_show", "reading_certificate", "growth_log", "growth_chart", "milestone_add",
           "milestones", "temperature_medicine_log", "temperature_medicine_show", "undo_last")


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "kids_logs",
        "description": "Logs for each child. action: 'reading_log' reading time and books (book, minutes, "
                       "finished; target = books per certificate); 'reading_show' reading log pop-up; "
                       "'reading_certificate' pop up their reading certificate; 'growth_log' height (height_cm) "
                       "and weight (weight_kg), convert feet/inches or stone first; 'growth_chart' (measure); "
                       "'milestone_add' firsts and milestones like first tooth, first steps, riding a bike "
                       "(text, date); 'milestones' pop-up; 'temperature_medicine_log' a sick child's temperature "
                       "in °C and medicine given (medicine, amount as the parent says it, note): a log only, never "
                       "suggest doses, suggest NHS 111 or the GP for worries; 'temperature_medicine_show'; "
                       "'undo_last' remove the last entry of a log (log), confirmed true only after the user "
                       "confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "child": {"type": "string", "description": "The child's first name."},
                "book": text,
                "minutes": {"type": "integer"},
                "finished": {"type": "boolean"},
                "target": {"type": "integer"},
                "height_cm": {"type": "number"},
                "weight_kg": {"type": "number"},
                "measure": {"type": "string", "enum": ["height", "weight"]},
                "text": text,
                "date": {"type": "string", "description": "YYYY-MM-DD, today, yesterday or a weekday."},
                "temperature": {"type": "number", "description": "°C."},
                "medicine": text,
                "amount": text,
                "note": text,
                "log": {"type": "string", "enum": list(LOGS)},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"kids_logs"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    kid = a("child")
    actions = {
        "reading_log": lambda: reading_log(settings, kid, a("book"), a("minutes"), a("finished"), a("date"),
                                           a("target")),
        "reading_show": lambda: reading_show(settings, kid),
        "reading_certificate": lambda: certificate(settings, kid),
        "growth_log": lambda: growth_log(settings, kid, a("height_cm"), a("weight_kg"), a("date")),
        "growth_chart": lambda: growth_chart(settings, kid, a("measure")),
        "milestone_add": lambda: milestone_add(settings, kid, a("text"), a("date")),
        "milestones": lambda: milestones(settings, kid),
        "temperature_medicine_log": lambda: health_log(settings, kid, a("temperature"), a("medicine"), a("amount"),
                                                       a("note")),
        "temperature_medicine_show": lambda: health_show(settings, kid),
        "undo_last": lambda: undo_last(settings, kid, a("log"), bool(a("confirmed"))),
    }
    if a("action") not in actions:
        raise ValueError(f"I can't do {a('action')} with the kids' logs.")
    return actions[a("action")]()
