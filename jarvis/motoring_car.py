"""The car itself: profile, MOT / tax / insurance / service due dates with reminders, the maintenance log with what's
next due, tyre pressure and tread notes, and a parking timer pop-up.

Everything is kept in motoring.json in the memory folder. The registration is shown only on the screen card and is
never spoken back, looked up or sent anywhere.
"""

from datetime import date, datetime, timedelta

import homestore as hs
import household_store as hstore
import motoring_store as ms
import reminders
import screen
from config import Settings

DATE_KINDS = ["mot", "tax", "insurance", "service", "breakdown cover", "other"]
POSITIONS = ["front left", "front right", "rear left", "rear right", "spare"]
SOON_DAYS = 30
REMIND_DAYS = 14
LOW_TREAD = 3.0
LEGAL_TREAD = 1.6
ACTIONS = ["profile_set", "profile_show", "date_set", "dates_show", "date_remove", "service_add", "service_show",
           "tyre_note", "tyre_show", "park_timer"]


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "motoring_car",
        "description": "The user's car. profile_set / profile_show (make, model, year, fuel, mpg, registration; the "
                       "registration stays on this PC); MOT, road tax, insurance, service due dates: date_set, "
                       "dates_show (countdowns, reminds 2 weeks before), date_remove; maintenance log (oil, tyres, "
                       "brakes, service) with next-due: service_add, service_show; tyre pressure and tread notes: "
                       "tyre_note, tyre_show; parking meter or pay-and-display timer: park_timer. date_remove needs "
                       "confirmed true, set only after the user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "make": text, "model": text, "year": {"type": "integer"},
                "fuel": {"type": "string", "enum": ["petrol", "diesel", "hybrid", "electric"]},
                "mpg": {"type": "number", "description": "Miles per UK gallon."},
                "reg": {"type": "string", "description": "Registration, kept locally only."},
                "kind": {"type": "string", "enum": DATE_KINDS},
                "due": {"type": "string", "description": "Due date, YYYY-MM-DD."},
                "job": {"type": "string", "description": "service_add: oil change, tyres, brakes, full service..."},
                "date": {"type": "string", "description": "YYYY-MM-DD, default today."},
                "miles": {"type": "number", "description": "Odometer reading in miles."},
                "cost": {"type": "number", "description": "Pounds."},
                "next_miles": {"type": "number", "description": "Odometer reading the job is next due at."},
                "next_months": {"type": "integer", "description": "Months until the job is next due."},
                "position": {"type": "string", "enum": POSITIONS + ["all"]},
                "psi": {"type": "number", "description": "Tyre pressure in psi."},
                "tread_mm": {"type": "number"},
                "minutes": {"type": "number", "description": "park_timer: how long the ticket lasts."},
                "note": text,
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"motoring_car"}


def run_tool(name: str, args: dict, settings: Settings):
    action = args.get("action")
    if action not in ACTIONS:
        raise ValueError(f"Unknown action {action}.")
    return globals()[action](settings, args)


# ---- profile -----------------------------------------------------------------------------

def profile_set(settings: Settings, args: dict) -> str:
    data = ms.load(settings)
    profile = data["profile"]
    for key in ("make", "model", "fuel"):
        if hs.clean(args.get(key), 40):
            profile[key] = hs.clean(args[key], 40)
    if args.get("year"):
        profile["year"] = int(ms.number(args["year"], "year", 1900, 2100))
    if args.get("mpg"):
        profile["mpg"] = ms.positive(args["mpg"], "mpg", 500)
    if hs.clean(args.get("reg"), 12):
        profile["reg"] = hs.clean(args["reg"], 12).upper()
    if not profile:
        raise ValueError("Tell me about the car: make, model, year, fuel, mpg or registration.")
    ms.save(settings, data)
    return f"Saved your car: {_title(profile) or 'details updated'}."


def _title(profile: dict) -> str:
    return " ".join(str(profile[k]) for k in ("year", "make", "model") if profile.get(k))


def profile_show(settings: Settings, args: dict) -> screen.Shown | str:
    profile = ms.load(settings)["profile"]
    if not profile:
        return "I don't have your car yet. Tell me its make, model and mpg."
    rows = [["Car", _title(profile) or "-"], ["Fuel", profile.get("fuel", "-").title()],
            ["MPG", f"{profile['mpg']:g}" if profile.get("mpg") else "-"],
            ["Registration", profile.get("reg", "-")]]
    said = f"Your car is a {_title(profile) or 'car'}" + (f" doing about {profile['mpg']:g} mpg." if profile.get("mpg") else ".")
    return screen.Shown(said, screen.card("table", "My car", "motoring-profile", columns=["", ""], rows=rows,
                                          text="The registration is stored only on this PC."))


# ---- due dates ---------------------------------------------------------------------------

def _status(due: date, today: date) -> str:
    left = (due - today).days
    if left < 0:
        return f"overdue by {-left} days"
    if left == 0:
        return "due today"
    return f"{left} days" + (" - soon" if left <= SOON_DAYS else "")


def date_set(settings: Settings, args: dict) -> str:
    kind = args.get("kind") if args.get("kind") in DATE_KINDS else "other"
    label = "MOT" if kind == "mot" else hs.clean(args.get("note"), 40) if kind == "other" and args.get("note") else kind.title()
    due = hs.parse_day(hs.need(args.get("due"), "due date"))
    data = ms.load(settings)
    data["dates"][label] = due.isoformat()
    ms.save(settings, data)
    return f"Saved: {label} due {hs.spoken(due)} {due.year}. {_remind(settings, label, due)}"


def _remind(settings: Settings, label: str, due: date) -> str:
    when = datetime.combine(due - timedelta(days=REMIND_DAYS), datetime.min.time()).replace(hour=9)
    try:
        reminders.add(settings, when.strftime("%Y-%m-%d %H:%M"), f"Your car's {label} is due on {hs.spoken(due)}.",
                      now=hs.now())
    except ValueError:
        return "It's less than 2 weeks away, so no reminder was needed."
    return f"I'll remind you {REMIND_DAYS} days before."


def dates_show(settings: Settings, args: dict) -> screen.Shown | str:
    found = ms.load(settings)["dates"]
    if not found:
        return "No car dates yet. Tell me when the MOT, tax or insurance is due."
    today = hs.today()
    rows = sorted(((date.fromisoformat(v), k) for k, v in found.items()))
    table = [[k, ms.short(d), _status(d, today)] for d, k in rows]
    first = rows[0]
    said = f"Next up: {first[1]} {_status(first[0], today)}."
    return screen.Shown(said, screen.card("table", "Car dates", "motoring-dates",
                                          columns=["What", "Due", "Days left"], rows=table))


def date_remove(settings: Settings, args: dict) -> str:
    data = ms.load(settings)
    key = hs.find(data["dates"], hs.need(args.get("kind") or args.get("note"), "date"))
    if key is None:
        raise ValueError("I haven't got that car date.")
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing the {key} date, then call again with confirmed true."
    del data["dates"][key]
    ms.save(settings, data)
    return f"Removed the {key} date."


# ---- maintenance -------------------------------------------------------------------------

def service_add(settings: Settings, args: dict) -> str:
    job = hs.need(args.get("job"), "job", 60)
    day = hs.parse_day(args.get("date"))
    entry = {"job": job, "date": day.isoformat()}
    if args.get("miles") is not None:
        entry["miles"] = ms.number(args["miles"], "mileage", 0, 1_000_000)
    if args.get("cost") is not None:
        entry["cost"] = ms.number(args["cost"], "cost", 0, 100_000)
    if args.get("next_miles") is not None:
        entry["next_miles"] = ms.number(args["next_miles"], "next due mileage", 0, 1_000_000)
    if args.get("next_months"):
        entry["next_date"] = _months_on(day, int(ms.number(args["next_months"], "months", 1, 120))).isoformat()
    ms.add(settings, "service", entry)
    due = f" Next due {ms.short(date.fromisoformat(entry['next_date']))}." if "next_date" in entry else ""
    return f"Logged {job} on {ms.short(day)}.{due}"


def _months_on(day: date, months: int) -> date:
    return hstore.add_months(day, months)


def service_show(settings: Settings, args: dict) -> screen.Shown | str:
    log = ms.load(settings)["service"]
    if not log:
        return "Nothing in the maintenance log yet."
    job = hs.clean(args.get("job"), 60).lower()
    log = [e for e in log if job in e["job"].lower()] if job else log
    if not log:
        return f"Nothing logged for {job}."
    rows = [[e["job"], ms.short(date.fromisoformat(e["date"])), f"{e['miles']:,.0f}" if "miles" in e else "",
             f"{e['cost']:.2f}" if "cost" in e else "", _next(e)] for e in reversed(log[-60:])]
    spent = sum(e.get("cost", 0) for e in log)
    latest = _latest_due(log)
    said = f"{len(log)} jobs logged, {spent:.2f} pounds in all." + (f" Next due: {latest}." if latest else "")
    return screen.Shown(said, screen.card("table", "Maintenance log", "motoring-service",
                                          columns=["Job", "Date", "Miles", "Cost", "Next due"], rows=rows))


def _next(entry: dict) -> str:
    bits = []
    if "next_date" in entry:
        bits.append(ms.short(date.fromisoformat(entry["next_date"])))
    if "next_miles" in entry:
        bits.append(f"{entry['next_miles']:,.0f} mi")
    return " or ".join(bits)


def _latest_due(log: list[dict]) -> str:
    newest = {e["job"].lower(): e for e in log}
    dues = [(e.get("next_date", "9999"), f"{e['job']} {_next(e)}") for e in newest.values() if _next(e)]
    return min(dues)[1] if dues else ""


# ---- tyres -------------------------------------------------------------------------------

def tyre_note(settings: Settings, args: dict) -> str:
    where = args.get("position") or "all"
    if where not in POSITIONS + ["all"]:
        raise ValueError(f"Which tyre? {', '.join(POSITIONS)}, or all.")
    if args.get("psi") is None and args.get("tread_mm") is None and not hs.clean(args.get("note")):
        raise ValueError("Give a pressure, a tread depth or a note.")
    data = ms.load(settings)
    for pos in POSITIONS[:4] if where == "all" else [where]:
        tyre = data["tyres"].setdefault(pos, {})
        if args.get("psi") is not None:
            tyre["psi"] = ms.positive(args["psi"], "pressure", 150)
        if args.get("tread_mm") is not None:
            tyre["tread_mm"] = ms.number(args["tread_mm"], "tread depth", 0, 12)
        if hs.clean(args.get("note"), 100):
            tyre["note"] = hs.clean(args["note"], 100)
        tyre["date"] = hs.today().isoformat()
    ms.save(settings, data)
    warn = ""
    if args.get("tread_mm") is not None and float(args["tread_mm"]) < LEGAL_TREAD:
        warn = " That is below the 1.6 mm legal limit, so replace the tyre."
    elif args.get("tread_mm") is not None and float(args["tread_mm"]) < LOW_TREAD:
        warn = " Getting low: consider replacing soon; 3 mm is a sensible limit."
    return f"Noted the {where} tyre{'s' if where == 'all' else ''}.{warn}"


def tyre_show(settings: Settings, args: dict) -> screen.Shown | str:
    tyres = ms.load(settings)["tyres"]
    if not tyres:
        return "No tyre notes yet."
    rows = [[pos.title(), f"{t['psi']:g}" if "psi" in t else "", f"{t['tread_mm']:g}" if "tread_mm" in t else "",
             ms.short(date.fromisoformat(t["date"])), t.get("note", "")] for pos in POSITIONS if (t := tyres.get(pos))]
    thin = [p for p in POSITIONS if tyres.get(p, {}).get("tread_mm", 9) < LOW_TREAD]
    said = "Your tyre notes are on screen." + (f" Low tread on the {', '.join(thin)}." if thin else "")
    return screen.Shown(said, screen.card("table", "Tyres", "motoring-tyres",
                                          columns=["Tyre", "psi", "Tread mm", "Checked", "Note"], rows=rows,
                                          text="Legal minimum tread is 1.6 mm."))


# ---- parking timer -----------------------------------------------------------------------

def park_timer(settings: Settings, args: dict) -> screen.Shown:
    minutes = ms.positive(args.get("minutes"), "minutes", 24 * 60)
    now = hs.now()
    ends = now + timedelta(minutes=minutes)
    note = hs.clean(args.get("note"), 80)
    if minutes > 10:
        try:
            reminders.add(settings, (ends - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M"),
                          "Your parking runs out in 5 minutes.", now=now)
        except ValueError:
            pass
    card = screen.card("timer", "Parking", "motoring-parking", ends_at=int(ends.timestamp() * 1000),
                       text=note or f"Ticket ends at {ends:%H:%M}.",
                       buttons=[{"label": "Add 30 minutes", "say": "Start a 30 minute parking timer."}])
    return screen.Shown(f"Parking timer set for {minutes:g} minutes; it ends at {ends:%H:%M}.", card)
