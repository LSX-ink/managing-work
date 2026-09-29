"""Pet records: profiles, age in human years, feeding schedule and who fed them, walks with a weekly chart,
training tricks and a pet sitter sheet saved as Markdown.

Everything is saved in petsgarden.json in the memory folder (the sitter sheet as petsgarden-sitter-sheet.md) and
never leaves the PC. Vet and vaccination dates are in the household pet care ability.
"""

import re
from datetime import date, datetime, timedelta

import homestore as hs
import petsgarden_store as store
from petsgarden_data import BREED_WORDS, BREEDS
import screen
from config import Settings

ACTIONS = ["profile", "show", "age", "remove", "feeding_schedule", "fed", "feed_check", "walk", "walk_week",
           "trick", "tricks", "sitter_sheet"]
LEVELS = ["learning", "practising", "mastered"]
SHEET = "petsgarden-sitter-sheet.md"
MAX_LOG = 400


def _pets(data: dict, name) -> tuple[dict, str]:
    """(the pets, the key asked for); no name is fine when there is only one pet."""
    pets = data["pets"]
    if not hs.clean(name) and len(pets) == 1:
        return pets, next(iter(pets))
    return pets, store.match(pets, name, "pet")


def _birthday(value) -> str:
    text = hs.clean(value)
    if not text:
        return ""
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        raise ValueError("Give the birthday as YYYY-MM-DD.") from None


def age_of(birthday: str, today: date) -> tuple[int, int]:
    """(whole years, extra months) since the birthday."""
    born = date.fromisoformat(birthday)
    months = (today.year - born.year) * 12 + today.month - born.month - (today.day < born.day)
    return max(0, months) // 12, max(0, months) % 12


def human_years(species: str, breed: str, years: int, months: int) -> float | None:
    """Rough human-age equivalent for dogs and cats; None for other pets."""
    age = years + months / 12
    species = species.lower()
    if species not in ("dog", "cat"):
        return None
    if age <= 1:
        return round(age * 15, 1)
    base = 15 + 9 * min(age - 1, 1)
    if age <= 2:
        return round(base, 1)
    if species == "cat":
        per = 4
    else:
        size = store_size(breed)
        per = {"small": 4, "medium": 5, "large": 6}[size]
    return round(base + (age - 2) * per, 1)


def store_size(breed: str) -> str:
    key = BREED_WORDS.get(breed.lower(), breed.lower())
    return BREEDS[key][0] if key in BREEDS else "medium"


def _age_text(pet: dict, today: date) -> str:
    if not pet.get("birthday"):
        return ""
    years, months = age_of(pet["birthday"], today)
    text = hs.plural(years, "year") if years else hs.plural(months, "month")
    if years and months:
        text += f" {hs.plural(months, 'month')}"
    human = human_years(pet.get("species", ""), pet.get("breed", ""), years, months)
    return text + (f" (about {human:g} in human years)" if human is not None else "")


def profile(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "pet", 40)
    data = store.load(settings)
    key = hs.find(data["pets"], name) or name
    if key not in data["pets"] and len(data["pets"]) >= 30:
        raise ValueError("That's a lot of pets; remove one first.")
    pet = data["pets"].setdefault(key, {"species": "", "breed": "", "birthday": "", "weight_kg": None, "notes": "",
                                        "feeding": {"times": [], "amount": ""}, "fed": [], "walks": [], "tricks": {}})
    for field, limit in (("species", 30), ("breed", 60), ("notes", 400)):
        if hs.clean(args.get(field)):
            pet[field] = hs.clean(args[field], limit).lower() if field == "species" else hs.clean(args[field], limit)
    if hs.clean(args.get("birthday")):
        pet["birthday"] = _birthday(args["birthday"])
    if args.get("weight_kg") is not None:
        pet["weight_kg"] = hs.number(args["weight_kg"], "weight", 0.05, 120)
    store.save(settings, data)
    return f"Saved {key}" + (f", a {pet['breed'] or pet['species']}" if pet["breed"] or pet["species"] else "") + "."


def show(settings: Settings, name, today: date) -> screen.Shown:
    data = store.load(settings)
    if not hs.clean(name) and len(data["pets"]) != 1:
        return _all(data, today)
    pets, key = _pets(data, name)
    pet = pets[key]
    feeding = pet["feeding"]
    rows = [["Species", pet["species"] or "not set"], ["Breed", pet["breed"] or "not set"],
            ["Birthday", hs.spoken(date.fromisoformat(pet["birthday"])) if pet["birthday"] else "not set"],
            ["Age", _age_text(pet, today) or "not set"],
            ["Weight", f"{pet['weight_kg']:g} kg" if pet["weight_kg"] else "not set"],
            ["Meals", ", ".join(feeding["times"]) + (f" ({feeding['amount']})" if feeding["amount"] else "") or "no schedule"],
            ["Tricks", ", ".join(pet["tricks"]) or "none yet"]]
    buttons = [{"label": "Walk chart", "say": f"Show {key}'s walks this week."},
               {"label": "Was fed today?", "say": f"Has {key} been fed today?"}]
    if pet["species"] == "dog":
        buttons.append({"label": "Breed facts", "say": f"Tell me about the breed {pet['breed'] or 'labrador'}."})
    card = screen.card("table", key, f"petsgarden-pet-{key}", buttons=buttons, columns=["", key], rows=rows)
    return screen.Shown(f"{key}'s profile is on the screen. {_age_text(pet, today)}".strip(), card)


def _all(data: dict, today: date) -> screen.Shown:
    if not data["pets"]:
        raise ValueError("I don't have any pets yet. Tell me a pet's name and what it is.")
    rows = [[k, p["species"] or "", p["breed"] or "", _age_text(p, today).split(" (")[0],
             f"{p['weight_kg']:g} kg" if p["weight_kg"] else ""] for k, p in data["pets"].items()]
    card = screen.card("table", "My pets", "petsgarden-pets", columns=["Name", "Kind", "Breed", "Age", "Weight"], rows=rows)
    return screen.Shown(f"You have {hs.plural(len(rows), 'pet')}: {', '.join(data['pets'])}.", card)


def age(settings: Settings, name, today: date) -> str:
    pets, key = _pets(store.load(settings), name)
    if not pets[key]["birthday"]:
        raise ValueError(f"I don't know {key}'s birthday yet. Tell me and I'll work it out.")
    return f"{key} is {_age_text(pets[key], today)}."


def remove(settings: Settings, name, confirmed: bool) -> str:
    data = store.load(settings)
    key = _pets(data, name)[1]
    if not confirmed:
        return f"Ask the user to confirm removing {key} and all their records, then call again with confirmed true."
    del data["pets"][key]
    store.save(settings, data)
    return f"Removed {key}."


def _times(values) -> list[str]:
    out = []
    for v in values or []:
        m = re.fullmatch(r"(\d{1,2})[:.]?(\d{2})?", hs.clean(v))
        if not m or int(m.group(1)) > 23 or int(m.group(2) or 0) > 59:
            raise ValueError("Give meal times like 08:00 and 17:30.")
        out.append(f"{int(m.group(1)):02d}:{m.group(2) or '00'}")
    return sorted(set(out))


def feeding_schedule(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    pets, key = _pets(data, args.get("name"))
    times = _times(args.get("times"))
    if not times:
        raise ValueError("Which meal times, like 08:00 and 17:30?")
    pets[key]["feeding"] = {"times": times, "amount": hs.clean(args.get("amount"), 80)}
    store.save(settings, data)
    return f"{key} is fed at {', '.join(times)}."


def fed(settings: Settings, args: dict, now: datetime) -> str:
    data = store.load(settings)
    pets, key = _pets(data, args.get("name"))
    who = hs.clean(args.get("who"), 40)
    pets[key]["fed"] = (pets[key]["fed"] + [{"at": now.isoformat(timespec="minutes"), "who": who}])[-MAX_LOG:]
    store.save(settings, data)
    today = sum(f["at"].startswith(now.date().isoformat()) for f in pets[key]["fed"])
    return f"Noted that {who + ' fed ' if who else ''}{key} at {now:%H:%M}. That's {hs.plural(today, 'meal')} today."


def feed_check(settings: Settings, name, now: datetime) -> screen.Shown:
    pets, key = _pets(store.load(settings), name)
    pet = pets[key]
    meals = [f for f in pet["fed"] if f["at"].startswith(now.date().isoformat())]
    due = [t for t in pet["feeding"]["times"] if t <= f"{now:%H:%M}"]
    lines = [f"{datetime.fromisoformat(m['at']):%H:%M}" + (f" by {m['who']}" if m["who"] else "") for m in meals]
    if not meals:
        said = f"Nobody has fed {key} today."
    else:
        said = f"{key} was fed today: " + "; ".join(lines) + "."
    if len(due) > len(meals):
        said += f" {hs.plural(len(due) - len(meals), 'scheduled meal')} looks missed."
    card = screen.card("list", f"Has {key} been fed?", f"petsgarden-fed-{key}",
                       items=[{"label": line, "done": True} for line in lines] or [{"label": "Nothing logged today"}],
                       buttons=[{"label": "Just fed", "say": f"I've just fed {key}."}])
    return screen.Shown(said, card)


def walk(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    pets, key = _pets(data, args.get("name"))
    minutes = hs.number(args.get("minutes"), "walk length in minutes", 1, 600)
    miles = hs.number(args.get("miles", 0), "distance in miles", 0, 100)
    day = hs.parse_day(args.get("day"), today)
    pets[key]["walks"] = (pets[key]["walks"] + [{"date": day.isoformat(), "minutes": minutes, "miles": miles}])[-MAX_LOG:]
    store.save(settings, data)
    week = sum(w["minutes"] for w in pets[key]["walks"] if hs.week_start(day).isoformat() <= w["date"])
    return f"Logged a {minutes:g} minute walk for {key}. That's {week:g} minutes this week."


def walk_week(settings: Settings, name, today: date) -> screen.Shown:
    pets, key = _pets(store.load(settings), name)
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    mins = [sum(w["minutes"] for w in pets[key]["walks"] if w["date"] == d.isoformat()) for d in days]
    miles = sum(w["miles"] for w in pets[key]["walks"] if w["date"] >= days[0].isoformat())
    card = screen.card("chart", f"{key}'s walks", f"petsgarden-walks-{key}", buttons=[
        {"label": "Log a walk", "say": f"Log a 30 minute walk for {key}."}],
        chart={"type": "bar", "labels": [d.strftime("%a") for d in days], "values": mins, "unit": "min"})
    return screen.Shown(f"{key} walked {sum(mins):g} minutes in the last week"
                        + (f", about {miles:g} miles." if miles else "."), card)


def trick(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    pets, key = _pets(data, args.get("name"))
    name = hs.need(args.get("trick"), "trick", 40).lower()
    level = hs.clean(args.get("level")).lower() or "learning"
    if level not in LEVELS:
        raise ValueError("The level is learning, practising or mastered.")
    tricks = pets[key]["tricks"]
    if name not in tricks and len(tricks) >= 40:
        raise ValueError("That's plenty of tricks already.")
    tricks[name] = level
    store.save(settings, data)
    return f"{key}'s {name} is now {level}."


def tricks(settings: Settings, name) -> screen.Shown:
    pets, key = _pets(store.load(settings), name)
    found = pets[key]["tricks"]
    if not found:
        raise ValueError(f"{key} has no tricks logged yet. Say what {key} is learning.")
    items = []
    for t, level in sorted(found.items(), key=lambda x: (-LEVELS.index(x[1]), x[0])):
        nxt = LEVELS[min(LEVELS.index(level) + 1, 2)]
        items.append({"label": f"{t}: {level}", "done": level == "mastered",
                      "say": "" if level == "mastered" else f"{key}'s trick {t} is now {nxt}."})
    done = sum(v == "mastered" for v in found.values())
    return screen.Shown(f"{key} has mastered {done} of {len(found)} tricks.",
                        screen.card("list", f"{key}'s tricks", f"petsgarden-tricks-{key}", items=items, checks=True))


def sitter_sheet(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    if not data["pets"]:
        raise ValueError("I don't have any pets to write a sheet for yet.")
    lines = ["# Pet sitter instructions", "", f"Written {date.today():%d %B %Y}. Please call me if anything worries you.", ""]
    if hs.clean(args.get("notes"), 600):
        lines += [hs.clean(args["notes"], 600), ""]
    for key, pet in data["pets"].items():
        lines += [f"## {key}", f"- Kind: {(pet['breed'] + ' ' if pet['breed'] else '') + pet['species']}".rstrip(),
                  f"- Weight: {pet['weight_kg']:g} kg" if pet["weight_kg"] else None,
                  f"- Meals: {', '.join(pet['feeding']['times']) or 'as usual'}"
                  + (f", {pet['feeding']['amount']}" if pet["feeding"]["amount"] else ""),
                  f"- Walks: {_walk_note(pet)}",
                  f"- Tricks: {', '.join(pet['tricks'])}" if pet["tricks"] else None,
                  f"- Notes: {pet['notes']}" if pet["notes"] else None, ""]
    lines += ["## Please remember", "- Never give chocolate, grapes, raisins, onion or anything sugar-free.",
              "- If a pet seems unwell, phone the vet first.", ""]
    path = hs.path(settings, SHEET)
    path.write_text("\n".join(line for line in lines if line is not None), encoding="utf-8")
    return screen.Shown(f"The pet sitter sheet for {len(data['pets'])} pets is saved and on the screen.",
                        screen.file_card(settings, path))


def _walk_note(pet: dict) -> str:
    walks = pet["walks"][-14:]
    if not walks:
        return "as usual"
    return f"usually about {round(sum(w['minutes'] for w in walks) / len(walks)):d} minutes"


# ---- The pet_records tool ----------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "pet_records",
        "description": "Pet profiles and daily care, kept privately. action: profile = add or update a pet (name, "
                       "species, breed, birthday YYYY-MM-DD, weight_kg, notes); show = a pet's profile card, or all "
                       "pets; age = pet's age and human years; remove (confirmed true only after the user says yes); "
                       "feeding_schedule = meal times and amount; fed = log a feed and who fed the dog or cat; "
                       "feed_check = did anyone feed the dog today; walk = log a dog walk (minutes, miles); "
                       "walk_week = weekly walk chart; trick = set a training trick's level (learning, practising, "
                       "mastered); tricks = the tricks list; sitter_sheet = pet sitter instructions saved as Markdown.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "The pet; may be left out when there is only one."},
                "species": {"type": "string", "description": "dog, cat, rabbit..."},
                "breed": {"type": "string"},
                "birthday": {"type": "string", "description": "YYYY-MM-DD."},
                "weight_kg": {"type": "number"},
                "notes": {"type": "string", "description": "profile: about the pet; sitter_sheet: a note for the sitter."},
                "times": {"type": "array", "items": {"type": "string"}, "description": "feeding_schedule: like 08:00."},
                "amount": {"type": "string", "description": "feeding_schedule: e.g. '1 cup'."},
                "who": {"type": "string", "description": "fed: who fed the pet."},
                "minutes": {"type": "number"},
                "miles": {"type": "number"},
                "day": {"type": "string", "description": "walk: YYYY-MM-DD, today or a weekday."},
                "trick": {"type": "string"},
                "level": {"type": "string", "enum": LEVELS},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"pet_records"}


def run_tool(name: str, args: dict, settings: Settings, http=None, now: datetime | None = None):
    now = now or datetime.now()
    today = now.date()
    action, pet = args.get("action"), args.get("name")
    if action == "profile":
        return profile(settings, args)
    if action == "show":
        return show(settings, pet, today)
    if action == "age":
        return age(settings, pet, today)
    if action == "remove":
        return remove(settings, pet, bool(args.get("confirmed")))
    if action == "feeding_schedule":
        return feeding_schedule(settings, args)
    if action == "fed":
        return fed(settings, args, now)
    if action == "feed_check":
        return feed_check(settings, pet, now)
    if action == "walk":
        return walk(settings, args, today)
    if action == "walk_week":
        return walk_week(settings, pet, today)
    if action == "trick":
        return trick(settings, args)
    if action == "tricks":
        return tricks(settings, pet)
    if action == "sitter_sheet":
        return sitter_sheet(settings, args)
    raise ValueError(f"Unknown pet action: {action}")
