"""Checklists for big home admin jobs (moving house, switching utilities) and a printable emergency info card.

Ticks and your own extra items are saved in homeadmin.json; the emergency card is also written as the Markdown file
"Home emergency card.md" in the memory folder so it can be printed.
"""

import homeadmin_store as store
import homestore as hs
import screen
from config import Settings

ACTIONS = ["list_show", "list_tick", "list_add", "emergency_set", "emergency_show"]
LISTS = {
    "moving": ("Moving house", [
        "Get three quotes from removal firms", "Book the removal firm or van", "Tell your employer and the bank",
        "Tell the council: council tax and electoral roll", "Redirect your post with Royal Mail",
        "Update the DVLA for your licence and car", "Tell your doctor, dentist and school", "Update your insurance",
        "Book time off for moving day", "Arrange a gas, electric and water final meter reading",
        "Switch or start energy and water at the new home", "Set up broadband at the new home",
        "Cancel or move your TV licence", "Pack an essentials box: kettle, chargers, loo roll",
        "Take meter photos on both handovers", "Collect all the keys", "Clean the old place",
        "Update your address on subscriptions and online shops"]),
    "switching": ("Switching utilities", [
        "Find your current tariff and end date", "Take a meter reading for each fuel",
        "Have your postcode and annual usage ready", "Compare deals on an Ofgem-accredited site",
        "Check exit fees on your current deal", "Pick a new tariff", "Give the new supplier your meter readings",
        "Check the switch confirmation email", "Note the cooling-off period, 14 days",
        "Read the meters on switch day", "Check the final bill from the old supplier",
        "Diarise the end date of the new deal"]),
}
NUMBERS = [("Emergency: police, fire, ambulance", "999"), ("Police, non-emergency", "101"),
           ("NHS health advice", "111"), ("Power cut", "105"), ("Gas emergency", "0800 111 999")]
FIELDS = ["stopcock", "fuse box", "gas meter", "electricity meter", "water meter", "boiler", "gas shut-off", "wifi router"]
MAX_CUSTOM = 40
CARD_FILE = "Home emergency card.md"


def _list(value) -> str:
    text = hs.clean(value).lower()
    if text.startswith(("mov", "house", "home")):
        return "moving"
    if text.startswith(("swi", "util", "energy", "supplier")):
        return "switching"
    raise ValueError("Which checklist: moving house, or switching utilities?")


def _items(data: dict, key: str) -> list[str]:
    return LISTS[key][1] + data["custom"].get(key, [])


def _phrase(key: str) -> str:
    return "moving house checklist" if key == "moving" else "utility switch checklist"


def list_show(settings: Settings, args: dict) -> screen.Shown:
    key, data = _list(args.get("list")), store.load(settings)
    ticks = data["checks"].get(key, {})
    items = [{"label": i, "done": bool(ticks.get(i)), "say": f"Tick off {i} on my {_phrase(key)}."} for i in _items(data, key)]
    done = sum(i["done"] for i in items)
    card = screen.card("list", LISTS[key][0], f"homeadmin-{key}", items=items, checks=True)
    todo = next((i["label"] for i in items if not i["done"]), None)
    text = f"{LISTS[key][0]}: {done} of {len(items)} done."
    return screen.Shown(text + (f" Next: {todo}." if todo else " All done."), card)


def list_tick(settings: Settings, args: dict) -> str:
    key, data = _list(args.get("list")), store.load(settings)
    item = store.match(_items(data, key), args.get("item"), "item")
    done = args.get("done") is not False
    data["checks"].setdefault(key, {})[item] = done
    store.save(settings, data)
    left = sum(not data["checks"][key].get(i) for i in _items(data, key))
    return f"{'Ticked off' if done else 'Unticked'} {item}. {hs.plural(left, 'thing')} left on the {_phrase(key)}."


def list_add(settings: Settings, args: dict) -> str:
    key, data = _list(args.get("list")), store.load(settings)
    item = hs.need(args.get("item"), "item", 100)
    extra = data["custom"].setdefault(key, [])
    if item.lower() in (i.lower() for i in _items(data, key)):
        raise ValueError("That's already on the list.")
    if len(extra) >= MAX_CUSTOM:
        raise ValueError("That checklist is full.")
    extra.append(item)
    store.save(settings, data)
    return f"Added {item} to the {_phrase(key)}."


# Emergency card

def emergency_set(settings: Settings, args: dict) -> str:
    field = hs.need(args.get("field"), "thing to note, like the stopcock", 40).lower()
    value = hs.need(args.get("value"), f"note for the {field}", 200)
    data = store.load(settings)
    field = hs.find(data["emergency"], field) or field
    if field not in data["emergency"] and len(data["emergency"]) >= MAX_CUSTOM:
        raise ValueError("The card is full; remove something first.")
    data["emergency"][field] = value
    store.save(settings, data)
    return f"Noted on the emergency card: {field}, {value}."


def card_markdown(emergency: dict) -> str:
    lines = ["# Home emergency card", "", "## Emergency numbers", ""]
    lines += [f"- **{label}:** {number}" for label, number in NUMBERS]
    lines += ["", "## Where things are", ""]
    ordered = [f for f in FIELDS if f in emergency] + [f for f in emergency if f not in FIELDS]
    lines += [f"- **{f.capitalize()}:** {emergency[f]}" for f in ordered]
    lines += [f"- **{f.capitalize()}:** _not filled in yet_" for f in FIELDS[:4] if f not in emergency]
    lines += ["", "If you smell gas: open the windows, no flames or switches, leave, call 0800 111 999."]
    return "\n".join(lines) + "\n"


def emergency_show(settings: Settings) -> screen.Shown:
    data = store.load(settings)
    text = card_markdown(data["emergency"])
    hs.path(settings, CARD_FILE).write_text(text, encoding="utf-8")
    card = screen.card("text", "Home emergency card", "homeadmin-emergency", text=text, buttons=[
        {"label": "Open to print", "say": f"Open the file {CARD_FILE} on my PC."}])
    missing = [f for f in FIELDS[:4] if f not in data["emergency"]]
    tail = f" You haven't noted the {', '.join(missing)} yet." if missing else ""
    return screen.Shown(f"The emergency card is on the screen and saved as {CARD_FILE}, ready to print.{tail}", card)


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "homeadmin_lists",
        "description": "Big home admin checklists and the emergency card. list_show, list_tick (item, done) and "
                       "list_add (item) for list = moving (moving house checklist) or switching (utility switch "
                       "checklist: energy, broadband). emergency_set (field = stopcock, fuse box, gas meter, boiler..., "
                       "value = where it is) and emergency_show the printable emergency info card with 999, 101, 111, "
                       "105 power cut numbers, saved as a Markdown file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "list": {"type": "string", "enum": ["moving", "switching"]},
                "item": text,
                "done": {"type": "boolean"},
                "field": text,
                "value": text,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"homeadmin_lists"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "emergency_show":
        return emergency_show(settings)
    handlers = {"list_show": list_show, "list_tick": list_tick, "list_add": list_add, "emergency_set": emergency_set}
    if action not in handlers:
        raise ValueError(f"Unknown checklist action: {action}")
    return handlers[action](settings, args)
