"""The house itself: appliance service logs and manuals, inventory photos for insurance, a month by month
maintenance calendar with ticks, and what an appliance costs to run.

Saved in homeadmin.json in the memory folder. Photos and manuals are files you already keep there.
"""

from datetime import date, timedelta

import homeadmin_store as store
import homestore as hs
import household_meters
import household_store as hh
import household_stuff
import screen
from config import Settings

ACTIONS = ["service_add", "service_show", "service_due", "inventory_photo", "inventory_check", "calendar_show",
           "calendar_tick", "calendar_add", "run_cost", "run_save", "run_list", "run_remove"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
JOBS = {
    1: ["Check for damp and condensation", "Clean the extractor fan filters"],
    2: ["Check the loft insulation", "Clean behind the fridge and freezer"],
    3: ["Look over the roof and loft for winter damage", "Clean the windows and frames"],
    4: ["Test the smoke and CO alarms", "Service the lawnmower"],
    5: ["Clean the patio and decking", "Check fences and gates"],
    6: ["Descale the washing machine and dishwasher", "Check the window and door seals"],
    7: ["Deep clean the oven and hob", "Check the shed and outside taps"],
    8: ["Wash the curtains and blinds", "Check the smoke alarm batteries"],
    9: ["Book the boiler service", "Clear the gutters and drains"],
    10: ["Bleed the radiators", "Test the smoke and CO alarms", "Service the boiler"],
    11: ["Fit draught excluders", "Turn off and drain the outside taps"],
    12: ["Check where the stopcock is", "Check the Christmas lights and fuses"],
}
DEFAULT_PENCE = 25.0
DAYS_PER_MONTH = 30.44


def _confirm(what: str, name: str) -> str:
    return f"Ask the user to confirm removing the {what} {name}, then call again with confirmed true."


# Service log and manuals

def service_add(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "appliance", 60)
    day = hs.parse_day(args.get("date"))
    data = store.load(settings)
    if name not in data["services"] and len(data["services"]) >= 60:
        raise ValueError("That's a lot of appliances; remove one first.")
    key = hs.find(data["services"], name) or name
    entry = data["services"].setdefault(key, {"manual": "", "next_due": "", "months": 0, "log": []})
    entry["log"] = (entry["log"] + [{"date": day.isoformat(), "note": hs.clean(args.get("note"), 200),
                                     "cost": round(hs.number(args.get("amount") or 0, "cost", 0, 100_000), 2)}])[-100:]
    if args.get("receipt"):
        entry["manual"] = store.receipt(settings, args.get("receipt"))
    months = int(hs.number(args.get("months") or entry["months"] or 0, "months", 0, 240))
    entry["months"] = months
    entry["next_due"] = hh.add_months(day, months).isoformat() if months else ""
    store.save(settings, data)
    tail = f" Next one is due {hs.spoken(date.fromisoformat(entry['next_due']))}." if entry["next_due"] else ""
    return f"Logged the {key} service on {hs.spoken(day)}.{tail}"


def service_show(settings: Settings, name=None) -> screen.Shown:
    today, services = hs.today(), store.load(settings)["services"]
    if not services:
        raise ValueError("No appliance services logged yet. Say what was serviced, when, and how often it's due.")
    if hs.clean(name):
        key = store.match(services, name, "appliance")
        entry = services[key]
        rows = [[e["date"], e["note"] or "-", store.money(e["cost"], settings) if e["cost"] else "-"]
                for e in reversed(entry["log"])]
        card = screen.card("table", f"{key}: service log", f"homeadmin-service-{key}", columns=["Date", "What", "Cost"],
                           rows=rows, buttons=store.file_button(entry["manual"], "Open manual"))
        due = f" Next due {hs.spoken(date.fromisoformat(entry['next_due']))}." if entry["next_due"] else ""
        return screen.Shown(f"{hs.plural(len(rows), 'service')} logged for the {key}.{due}", card)
    rows = [[k, e["log"][-1]["date"] if e["log"] else "-", e["next_due"] or "-",
             store.when(date.fromisoformat(e["next_due"]), today) if e["next_due"] else "-", e["manual"] or "-"]
            for k, e in sorted(services.items())]
    card = screen.card("table", "Appliance services", "homeadmin-services",
                       columns=["Appliance", "Last service", "Next due", "When", "Manual"], rows=rows)
    return screen.Shown(f"{hs.plural(len(rows), 'appliance')} in the service log.", card)


def service_due(settings: Settings, days=None) -> screen.Shown | str:
    today = hs.today()
    limit = today + timedelta(days=int(hs.number(days if days is not None else 60, "number of days", 1, 3650)))
    due = sorted((e["next_due"], k) for k, e in store.load(settings)["services"].items()
                 if e["next_due"] and date.fromisoformat(e["next_due"]) <= limit)
    if not due:
        return "Nothing needs servicing soon."
    items = [{"label": f"{k}: {store.when(date.fromisoformat(d), today)}", "say": f"I've had the {k} serviced today."}
             for d, k in due]
    return screen.Shown(f"{hs.plural(len(due), 'appliance')} due a service; first is {due[0][1]}, "
                        f"{store.when(date.fromisoformat(due[0][0]), today)}.",
                        screen.card("list", "Services due", "homeadmin-services-due", items=items))


# Inventory photos for insurance

def inventory_photo(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "item", 60)
    path = store.receipt(settings, args.get("receipt"))
    if not path:
        raise ValueError("Which photo? Give its path in the memory folders, like Home/Photos/tv.jpg.")
    inventory = hh.rows(settings, household_stuff.INVENTORY)
    key = hs.find(inventory, name) or name
    data = store.load(settings)
    data["photos"][key] = path
    store.save(settings, data)
    return f"Saved the photo for {key}." + ("" if key in inventory else " It isn't in your home inventory yet.")


def inventory_check(settings: Settings) -> screen.Shown:
    inventory = hh.rows(settings, household_stuff.INVENTORY)
    if not inventory:
        raise ValueError("Your home inventory is empty. Add items with their room and value first.")
    photos = {k.lower() for k in store.load(settings)["photos"]}
    rooms: dict[str, list] = {}
    for k, r in inventory.items():
        rooms.setdefault(r["room"], []).append((k, r["value"], k.lower() in photos))
    rows = [[room, str(len(v)), store.money(sum(x[1] for x in v), settings), f"{sum(x[2] for x in v)} of {len(v)}"]
            for room, v in sorted(rooms.items())]
    total = sum(r["value"] for r in inventory.values())
    rows.append(["Total", str(len(inventory)), store.money(total, settings), f"{sum(k.lower() in photos for k in inventory)} of {len(inventory)}"])
    missing = [k for k in inventory if k.lower() not in photos]
    card = screen.card("table", "Contents for insurance", "homeadmin-insurance",
                       columns=["Room", "Items", "Value", "With photo"], rows=rows)
    text = f"Contents come to {store.money(total, settings)}."
    if missing:
        text += f" {hs.plural(len(missing), 'item')} without a photo, like {', '.join(missing[:3])}."
    return screen.Shown(text, card)


# Maintenance calendar

def _month(value, today: date) -> int:
    text = hs.clean(value).lower()
    if not text:
        return today.month
    if text.isdigit() and 1 <= int(text) <= 12:
        return int(text)
    for i, name in enumerate(MONTHS):
        if len(text) >= 3 and name.lower().startswith(text):
            return i + 1
    raise ValueError("Which month? Say a name like March.")


def _jobs(data: dict, month: int) -> list[str]:
    return JOBS[month] + [j["job"] for j in data["extra_jobs"] if j["month"] == month]


def _tick_key(year: int, month: int, job: str) -> str:
    return f"{year}-{month:02d}:{job.lower()}"


def calendar_show(settings: Settings, month=None) -> screen.Shown:
    today, data = hs.today(), store.load(settings)
    if hs.clean(month).lower() == "all":
        rows = []
        for m in range(1, 13):
            jobs = _jobs(data, m)
            done = sum(data["ticks"].get(_tick_key(today.year, m, j), False) for j in jobs)
            rows.append([MONTHS[m - 1], f"{done} of {len(jobs)}", "; ".join(jobs)])
        return screen.Shown(f"Here's the home maintenance year for {today.year}.",
                            screen.card("table", f"Home maintenance {today.year}", "homeadmin-calendar-year",
                                        columns=["Month", "Done", "Jobs"], rows=rows))
    m = _month(month, today)
    jobs = _jobs(data, m)
    items = [{"label": j, "done": bool(data["ticks"].get(_tick_key(today.year, m, j))),
              "say": f"Tick off {j} for {MONTHS[m - 1]} on my home maintenance calendar."} for j in jobs]
    done = sum(i["done"] for i in items)
    card = screen.card("list", f"Home jobs: {MONTHS[m - 1]}", f"homeadmin-calendar-{m}", items=items, checks=True,
                       buttons=[{"label": "Whole year", "say": "Show my home maintenance for the whole year."}])
    return screen.Shown(f"{MONTHS[m - 1]} has {hs.plural(len(jobs), 'job')}, {done} done.", card)


def calendar_tick(settings: Settings, args: dict) -> str:
    today, data = hs.today(), store.load(settings)
    m = _month(args.get("month"), today)
    job = store.match(_jobs(data, m), args.get("name"), "job")
    done = args.get("done") is not False
    data["ticks"][_tick_key(today.year, m, job)] = done
    store.save(settings, data)
    left = sum(not data["ticks"].get(_tick_key(today.year, m, j)) for j in _jobs(data, m))
    return f"{'Ticked off' if done else 'Unticked'} {job}. {hs.plural(left, 'job')} left in {MONTHS[m - 1]}."


def calendar_add(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    m = _month(args.get("month"), hs.today())
    job = hs.need(args.get("name"), "job", 80)
    data["extra_jobs"] = store.add(data["extra_jobs"], {"month": m, "job": job})
    store.save(settings, data)
    return f"Added {job} to {MONTHS[m - 1]}."


# Running costs

def _pence(settings: Settings, value) -> tuple[float, bool]:
    if value is not None:
        return hs.number(value, "price per kWh in pence", 0.1, 1000), True
    saved = hs.load(settings, household_meters.METERS, {}).get("prices", {}).get("electric")
    return (float(saved) * 100, True) if isinstance(saved, (int, float)) and saved > 0 else (DEFAULT_PENCE, False)


def run_cost(settings: Settings, args: dict) -> screen.Shown:
    name = hs.clean(args.get("name"), 60)
    saved = store.load(settings)["appliances"]
    found = hs.find(saved, name) if name else None
    known = saved.get(found) if found else None
    name = found or name
    watts = args.get("watts") if args.get("watts") is not None else known and known["watts"]
    hours = args.get("hours") if args.get("hours") is not None else known and known["hours"]
    watts = hs.number(watts, "wattage", 0.1, 100_000)
    hours = hs.number(hours, "hours a day", 0.01, 24)
    pence, given = _pence(settings, args.get("pence"))
    day_kwh = watts / 1000 * hours
    rows = [[label, f"{day_kwh * n:.2f} kWh", store.money(day_kwh * n * pence / 100, settings)]
            for label, n in (("Per day", 1), ("Per week", 7), ("Per month", DAYS_PER_MONTH), ("Per year", 365))]
    title = f"Running cost: {name}" if name else "Running cost"
    card = screen.card("table", title, "homeadmin-run-cost", columns=["", "Energy", "Cost"], rows=rows,
                       buttons=[{"label": "Save it", "say": f"Save {name or 'this appliance'} at {watts:g} watts, {hours:g} hours a day."}]
                       if name and not known else [])
    note = "" if given else f" (using {DEFAULT_PENCE:g}p per kWh; tell me your rate for a better figure)"
    return screen.Shown(f"{name or 'It'} at {watts:g} watts for {hours:g} hours a day costs about "
                        f"{store.money(day_kwh * pence / 100, settings)} a day, {store.money(day_kwh * DAYS_PER_MONTH * pence / 100, settings)} "
                        f"a month, {store.money(day_kwh * 365 * pence / 100, settings)} a year{note}.", card)


def run_save(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "appliance", 60)
    data = store.load(settings)
    key = hs.find(data["appliances"], name) or name
    if key not in data["appliances"] and len(data["appliances"]) >= 100:
        raise ValueError("That's a lot of appliances; remove one first.")
    data["appliances"][key] = {"watts": hs.number(args.get("watts"), "wattage", 0.1, 100_000),
                               "hours": hs.number(args.get("hours"), "hours a day", 0.01, 24)}
    store.save(settings, data)
    return f"Saved {key}: {data['appliances'][key]['watts']:g} watts, {data['appliances'][key]['hours']:g} hours a day."


def run_list(settings: Settings, args: dict) -> screen.Shown:
    saved = store.load(settings)["appliances"]
    if not saved:
        raise ValueError("No appliances saved yet. Say the name, its watts and hours a day.")
    pence, given = _pence(settings, args.get("pence"))
    ranked = sorted(((a["watts"] / 1000 * a["hours"] * 365 * pence / 100, k, a) for k, a in saved.items()), reverse=True)
    rows = [[k, f"{a['watts']:g} W", f"{a['hours']:g} h", store.money(cost / 12, settings), store.money(cost, settings)]
            for cost, k, a in ranked]
    total = sum(c for c, _, _ in ranked)
    rows.append(["Total", "", "", store.money(total / 12, settings), store.money(total, settings)])
    card = screen.card("table", "Appliance running costs", "homeadmin-run-list",
                       columns=["Appliance", "Power", "Hours a day", "Per month", "Per year"], rows=rows)
    return screen.Shown(f"{ranked[0][1]} costs the most to run, about {store.money(ranked[0][0], settings)} a year, at {pence:g}p per kWh.", card)


def run_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    key = store.match(data["appliances"], args.get("name"), "appliance")
    if not args.get("confirmed"):
        return _confirm("appliance", key)
    del data["appliances"][key]
    store.save(settings, data)
    return f"Removed {key}."


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "homeadmin_home",
        "description": "Running the house. Appliance service log: service_add (name = boiler, oven..., date, note, "
                       "amount = cost, months = how often, receipt = manual file path in the memory folders), "
                       "service_show (optional name; shows the log and manual), service_due. Insurance contents: "
                       "inventory_photo (name of an inventory item, receipt = photo path), inventory_check totals by "
                       "room and which have no photo. Maintenance calendar by month (gutters, smoke alarm test, boiler "
                       "service, bleed radiators): calendar_show (month name, or 'all'), calendar_tick (name = job, "
                       "month, done), calendar_add (name, month). Cost of running an appliance: run_cost (watts, hours "
                       "per day, pence = p per kWh, optional name of a saved one), run_save (name, watts, hours), "
                       "run_list ranks saved ones, run_remove. Set confirmed true only after the user confirms a remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": text,
                "date": {"type": "string", "description": "YYYY-MM-DD or 'today'."},
                "note": text,
                "amount": {"type": "number"},
                "months": {"type": "integer"},
                "receipt": {"type": "string", "description": "A file path like Home/Manuals/boiler.pdf."},
                "days": {"type": "integer"},
                "month": {"type": "string"},
                "done": {"type": "boolean"},
                "watts": {"type": "number"},
                "hours": {"type": "number"},
                "pence": {"type": "number", "description": "Electricity price in pence per kWh."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"homeadmin_home"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "service_show":
        return service_show(settings, args.get("name"))
    if action == "service_due":
        return service_due(settings, args.get("days"))
    if action == "calendar_show":
        return calendar_show(settings, args.get("month"))
    if action == "inventory_check":
        return inventory_check(settings)
    handlers = {"service_add": service_add, "inventory_photo": inventory_photo, "calendar_tick": calendar_tick,
                "calendar_add": calendar_add, "run_cost": run_cost, "run_save": run_save, "run_list": run_list,
                "run_remove": run_remove}
    if action not in handlers:
        raise ValueError(f"Unknown home action: {action}")
    return handlers[action](settings, args)
