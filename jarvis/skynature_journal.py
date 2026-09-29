"""Nature journal: birds, animals, plants and other sightings with date and place, counts by species, first of the
year, a bird life list with yearly totals, a monthly chart and places.

Saved in skynature-journal.json in the memory folder on this PC and nowhere else.
"""

from datetime import date

import homestore as hs
import screen
from config import Settings
from skynature_wild_data import BIRDS, MONTHS

FILE = "skynature-journal.json"
MAX_SIGHTINGS = 5000
KINDS = ["bird", "animal", "plant", "insect", "fungus", "other"]
ACTIONS = ["add", "list", "species_counts", "first_of_year", "life_list", "monthly", "places", "delete"]


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    return {"next": int(found.get("next") or 1),
            "sightings": [s for s in found.get("sightings") or [] if isinstance(s, dict)]}


def _nice(species: str) -> str:
    return species[:1].upper() + species[1:].lower()


def _canon(species: str, known: list[str]) -> str:
    """The spelling already used for this species (any case), else the bird table's, else tidied."""
    name = hs.need(species, "species", 60)
    for k in known + list(BIRDS):
        if k.lower() == name.lower():
            return k
    return _nice(name)


def _date(value, today: date) -> date:
    if not value:
        return today
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError("Give the date as year-month-day, like 2026-09-27.") from None


def _matches(s: dict, args: dict) -> bool:
    d = s["date"]
    if args.get("kind") and s["kind"] != args["kind"]:
        return False
    if args.get("species") and args["species"].lower() not in s["species"].lower():
        return False
    if args.get("year") and d[:4] != str(int(args["year"])):
        return False
    if args.get("month") and int(d[5:7]) != int(args["month"]):
        return False
    return True


def _line(s: dict) -> str:
    when = date.fromisoformat(s["date"])
    extra = f" x{s['count']}" if s["count"] > 1 else ""
    return f"#{s['id']} {when.day} {when:%b %Y}: {s['species']}{extra}" + (f", {s['place']}" if s["place"] else "")


def add(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = load(settings)
    if len(data["sightings"]) >= MAX_SIGHTINGS:
        raise ValueError("The journal is full; delete some old sightings first.")
    known = sorted({s["species"] for s in data["sightings"]})
    species = _canon(args.get("species"), known)
    d = _date(args.get("date"), today)
    kind = args.get("kind") or ("bird" if species in BIRDS else next(
        (s["kind"] for s in data["sightings"] if s["species"] == species), "other"))
    if kind not in KINDS:
        raise ValueError(f"Kind should be one of {', '.join(KINDS)}.")
    count = min(max(int(args.get("count") or 1), 1), 10000)
    entry = {"id": data["next"], "date": d.isoformat(), "species": species, "kind": kind,
             "place": hs.clean(args.get("place"), 60), "count": count, "note": hs.clean(args.get("note"), 200)}
    earlier = [s for s in data["sightings"] if s["species"] == species and s["date"] < d.isoformat()]
    this_year = [s for s in data["sightings"] if s["species"] == species and s["date"][:4] == str(d.year)]
    data["sightings"].append(entry)
    data["next"] += 1
    hs.save(settings, FILE, data)
    said = f"Logged {species}{f' x{count}' if count > 1 else ''} on {d.day} {d:%B}" + (f" at {entry['place']}" if entry["place"] else "") + "."
    if not earlier and kind == "bird":
        said += " That's a new one for your bird life list!"
    elif not earlier:
        said += " That's the first time you've logged it."
    if not this_year:
        said += f" It's your first {species.lower()} of {d.year}."
    return screen.Shown(said, screen.card("text", "Sighting logged", "skynature-sighting", text=_line(entry) + (
        f"\n{entry['note']}" if entry["note"] else ""), buttons=[
        {"label": "Species counts", "say": "How many of each species have I logged?"},
        {"label": "First of the year", "say": "What are my first sightings this year?"}]))


def listing(settings: Settings, args: dict) -> screen.Shown:
    found = [s for s in load(settings)["sightings"] if _matches(s, args)]
    if not found:
        return screen.Shown("Nothing matches in your nature journal yet.", screen.card(
            "text", "Nature journal", "skynature-journal", text="No sightings match."))
    recent = sorted(found, key=lambda s: (s["date"], s["id"]), reverse=True)[:min(max(int(args.get("limit") or 20), 1), 60)]
    items = [{"label": _line(s), "say": f"Show my {s['species']} sightings."} for s in recent]
    said = f"{len(found)} sightings. The latest is {recent[0]['species']} on {recent[0]['date']}."
    return screen.Shown(said, screen.card("list", "Nature journal", "skynature-journal", items=items))


def _by_species(sightings: list[dict]) -> dict:
    out: dict = {}
    for s in sorted(sightings, key=lambda s: (s["date"], s["id"])):
        row = out.setdefault(s["species"].lower(), {"name": s["species"], "kind": s["kind"], "times": 0, "seen": 0,
                                                    "first": s["date"], "place": s["place"], "last": s["date"]})
        row["times"] += 1
        row["seen"] += s["count"]
        row["last"] = s["date"]
    return out


def species_counts(settings: Settings, args: dict) -> screen.Shown:
    rows = _by_species([s for s in load(settings)["sightings"] if _matches(s, args)])
    if not rows:
        return screen.Shown("Nothing logged yet for that.", screen.card("text", "Species counts", "skynature-counts",
                                                                         text="Nothing logged yet."))
    ranked = sorted(rows.values(), key=lambda r: (-r["times"], -r["seen"], r["name"]))[:40]
    said = (f"{len(rows)} species logged. Most seen: " +
            ", ".join(f"{r['name']} ({r['times']} sighting{'s' if r['times'] != 1 else ''})" for r in ranked[:3]) + ".")
    table = [[r["name"], r["kind"], r["times"], r["seen"], r["first"], r["last"]] for r in ranked]
    return screen.Shown(said, screen.card("table", "Species counts", "skynature-counts",
                                          columns=["Species", "Kind", "Sightings", "Individuals", "First", "Last"], rows=table))


def first_of_year(settings: Settings, args: dict, today: date) -> screen.Shown:
    year = int(args.get("year") or today.year)
    sightings = load(settings)["sightings"]
    ever = _by_species([s for s in sightings if s["date"][:4] < str(year)])
    rows = sorted(_by_species([s for s in sightings if s["date"][:4] == str(year) and _matches(s, {"kind": args.get("kind")})]).values(),
                  key=lambda r: r["first"])
    if not rows:
        return screen.Shown(f"You haven't logged anything in {year} yet.", screen.card(
            "text", f"First of {year}", "skynature-firsts", text="Nothing logged yet."))
    table = [[r["name"], r["first"], r["place"] or "", "" if r["name"].lower() in ever else "new"] for r in rows]
    latest = rows[-1]
    said = (f"You have {len(rows)} species so far in {year}. First was {rows[0]['name']} on {rows[0]['first']}, "
            f"and the latest new one is {latest['name']} on {latest['first']}.")
    return screen.Shown(said, screen.card("table", f"First sightings {year}", "skynature-firsts",
                                          columns=["Species", "First seen", "Where", "Life"], rows=table))


def life_list(settings: Settings, args: dict, today: date) -> screen.Shown:
    kind = args.get("kind") or "bird"
    rows = sorted(_by_species([s for s in load(settings)["sightings"] if s["kind"] == kind]).values(), key=lambda r: r["name"])
    if not rows:
        return screen.Shown(f"Your {kind} life list is empty. Tell me what you spot and I'll start it.", screen.card(
            "text", f"{kind.title()} life list", "skynature-life", text="Empty so far."))
    years: dict[str, int] = {}
    for r in rows:
        years[r["first"][:4]] = years.get(r["first"][:4], 0) + 1
    seen_this_year = len({s["species"].lower() for s in load(settings)["sightings"]
                          if s["kind"] == kind and s["date"][:4] == str(today.year)})
    said = (f"Your {kind} life list has {len(rows)} species, and you've seen {seen_this_year} so far in {today.year}. "
            "New species by year: " + ", ".join(f"{y}: {n}" for y, n in sorted(years.items())) + ".")
    table = [[r["name"], r["first"], r["place"] or "", r["times"]] for r in rows]
    return screen.Shown(said, screen.card(
        "table", f"{kind.title()} life list ({len(rows)})", "skynature-life",
        columns=["Species", "First seen", "Where", "Times"], rows=table,
        buttons=[{"label": "This year's firsts", "say": "What are my first sightings this year?"}]))


def monthly(settings: Settings, args: dict, today: date) -> screen.Shown:
    year = int(args.get("year") or today.year)
    found = [s for s in load(settings)["sightings"] if s["date"][:4] == str(year) and _matches(s, {"kind": args.get("kind")})]
    if not found:
        return screen.Shown(f"Nothing logged in {year} yet.", screen.card("text", f"Sightings {year}", "skynature-monthly",
                                                                        text="Nothing logged yet."))
    counts = [len({s["species"].lower() for s in found if int(s["date"][5:7]) == m}) for m in range(1, 13)]
    best = counts.index(max(counts))
    said = f"{MONTHS[best]} was your best month in {year}, with {counts[best]} species."
    return screen.Shown(said, screen.card("chart", f"Species per month {year}", "skynature-monthly", chart={
        "type": "bar", "labels": [m[:3] for m in MONTHS], "values": counts, "unit": "species"}))


def places(settings: Settings) -> screen.Shown:
    out: dict = {}
    for s in load(settings)["sightings"]:
        if s["place"]:
            row = out.setdefault(s["place"].lower(), {"name": s["place"], "n": 0, "species": set()})
            row["n"] += 1
            row["species"].add(s["species"].lower())
    if not out:
        return screen.Shown("None of your sightings have a place yet.", screen.card("text", "Places", "skynature-places",
                                                                                       text="No places logged."))
    ranked = sorted(out.values(), key=lambda r: (-len(r["species"]), r["name"]))[:30]
    said = f"Your richest spot is {ranked[0]['name']} with {len(ranked[0]['species'])} species."
    return screen.Shown(said, screen.card("table", "Where you spot things", "skynature-places", columns=["Place", "Sightings", "Species"],
                                          rows=[[r["name"], r["n"], len(r["species"])] for r in ranked]))


def delete(settings: Settings, args: dict) -> str:
    data = load(settings)
    target = next((s for s in data["sightings"] if s["id"] == args.get("id")), None)
    if not target:
        raise ValueError("Which sighting? Ask me to list them and give the number.")
    if not args.get("confirmed"):
        return f"Delete {_line(target)}? Say yes and I'll remove it."
    data["sightings"].remove(target)
    hs.save(settings, FILE, data)
    return f"Removed {_line(target)}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "nature_journal",
        "description": "The user's nature journal of birds, animals, plants and insects they've spotted. action: add = "
                       "log a sighting (species; optional date, place, count, note, kind); list = recent sightings "
                       "(filter by kind, species, year, month); species_counts = how many of each species; "
                       "first_of_year = first sighting of each species this year; life_list = bird life list with "
                       "yearly totals; monthly = chart of species per month; places = where they spot most; delete = "
                       "remove a sighting by id, set confirmed true only after the user says yes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "species": {"type": "string", "description": "add: what was seen. list and counts: optional filter."},
                "kind": {"type": "string", "enum": KINDS},
                "date": {"type": "string", "description": "add: YYYY-MM-DD, default today."},
                "place": {"type": "string"}, "count": {"type": "integer"}, "note": {"type": "string"},
                "year": {"type": "integer"}, "month": {"type": "integer"}, "limit": {"type": "integer"},
                "id": {"type": "integer", "description": "delete: the sighting number shown in the list."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"nature_journal"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or hs.today()
    action = args.get("action")
    if action == "add":
        return add(settings, args, today)
    if action == "list":
        return listing(settings, args)
    if action == "species_counts":
        return species_counts(settings, args)
    if action == "first_of_year":
        return first_of_year(settings, args, today)
    if action == "life_list":
        return life_list(settings, args, today)
    if action == "monthly":
        return monthly(settings, args, today)
    if action == "places":
        return places(settings)
    if action == "delete":
        return delete(settings, args)
    raise ValueError(f"Unknown journal action: {action}")
