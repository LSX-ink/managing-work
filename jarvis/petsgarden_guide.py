"""Pet guide from built-in tables: which foods are toxic to dogs and cats, a first-aid kit checklist and steps,
and dog breed facts with a picture from dog.ceo (keyless; only the breed word is sent).

General guidance, not veterinary advice. Anything serious means phoning the vet.
"""

import screen
from config import Settings
from feeds import fetch_json
import homestore as hs
from petsgarden_data import BREED_WORDS, BREEDS, DOG_CEO, FIRST_AID, FIRST_AID_KIT, TOXIC

ACTIONS = ["toxic_food", "first_aid", "breed_facts"]
DOG_API = "https://dog.ceo/api"
ICON = {"toxic": "TOXIC", "caution": "Caution", "ok": "Safe"}
VET_NOTE = "If your pet has eaten something dangerous, phone your vet straight away."


def _stem(word: str) -> str:
    return word[:-3] + "y" if word.endswith("ies") else word.rstrip("s")


def toxic_food(food, species) -> screen.Shown:
    species = hs.clean(species).lower()
    text = hs.clean(food).lower()
    if not text:
        rows = [[f, ICON[d], ICON[c]] for f, (d, c, _) in sorted(TOXIC.items(), key=lambda x: (x[1][0] != "toxic", x[0]))]
        card = screen.card("table", "Foods and pets", "petsgarden-toxic", columns=["Food", "Dogs", "Cats"], rows=rows)
        return screen.Shown("Here's the list of foods; the toxic ones come first. " + VET_NOTE, card)
    found = [k for k in TOXIC if _stem(k) in _stem(text) or _stem(text) in _stem(k)]
    if not found:
        said = f"I don't have {text} in my table, so check with your vet before feeding it. " + VET_NOTE
        return screen.Shown(said, screen.card("text", f"Is {text} safe?", "petsgarden-toxic-one", text=said))
    rows = [[k, ICON[TOXIC[k][0]], ICON[TOXIC[k][1]], TOXIC[k][2]] for k in found[:8]]
    first = TOXIC[found[0]]
    level = first[1] if species == "cat" else first[0]
    who = "cats" if species == "cat" else "dogs"
    verdict = {"toxic": "is toxic", "caution": "needs caution", "ok": "is generally safe"}[level]
    said = f"{found[0].capitalize()} {verdict} for {who}. {first[2]}" + (" " + VET_NOTE if level == "toxic" else "")
    card = screen.card("table", f"Is {found[0]} safe?", "petsgarden-toxic-one", columns=["Food", "Dogs", "Cats", "Why"],
                       rows=rows, buttons=[{"label": "All foods", "say": "Show me the list of foods that are toxic to pets."}])
    return screen.Shown(said, card)


def first_aid(topic) -> screen.Shown:
    text = hs.clean(topic).lower()
    if not text:
        items = [{"label": item} for item in FIRST_AID_KIT]
        buttons = [{"label": t.capitalize(), "say": f"Pet first aid for {t}."} for t in list(FIRST_AID)[:6]]
        return screen.Shown("Here's a first-aid kit checklist for your pets. Tick things off as you gather them.",
                            screen.card("list", "Pet first-aid kit", "petsgarden-firstaid", items=items, checks=True,
                                        buttons=buttons))
    key = next((k for k in FIRST_AID if k in text or text in k), None)
    if key is None:
        raise ValueError("I have first aid for: " + ", ".join(FIRST_AID) + ".")
    said = f"{FIRST_AID[key]} Phone your vet on the way."
    return screen.Shown(said, screen.card("text", f"Pet first aid: {key}", f"petsgarden-firstaid-{key}", text=said,
                                          buttons=[{"label": "Kit checklist", "say": "Show the pet first-aid kit checklist."}]))


def _breed(name) -> str:
    text = hs.need(name, "breed", 60).lower()
    text = BREED_WORDS.get(text, text)
    return next((k for k in BREEDS if text == k or text in k), text)


async def breed_facts(http, name) -> screen.Shown:
    breed = _breed(name)
    facts = BREEDS.get(breed)
    path = DOG_CEO.get(breed, breed.replace(" ", ""))
    image = ""
    try:
        body = await fetch_json(http, f"{DOG_API}/breed/{path}/images/random", "dog picture")
        image = body.get("message", "") if isinstance(body, dict) else ""
    except ValueError:
        if facts is None:
            raise ValueError(f"I don't know the breed {breed}.") from None
    if facts is None and not image:
        raise ValueError(f"I don't know the breed {breed}.")
    title = breed.title()
    if facts:
        lines = [f"Size: {facts[0]}", f"Weight: {facts[1]}", f"Life span: {facts[2]}", f"Exercise: {facts[3]}", facts[4]]
        said = f"{title}: {facts[0]} dog, {facts[3]} of exercise, lives {facts[2]}. {facts[4]}"
    else:
        lines = ["I have no facts on that breed yet."]
        said = f"Here's a picture of a {title}. I have no facts on that breed yet."
    image = image if image.startswith("https://images.dog.ceo/") else ""
    card = screen.card("reader", title, f"petsgarden-breed-{breed}", text="\n\n".join(lines), image=image, site="dog.ceo",
                       buttons=[{"label": "Another picture", "say": f"Show me another picture of a {breed}."}])
    return screen.Shown(said, card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "pet_guide",
        "description": "Pet safety and breed facts from built-in tables. action: toxic_food = is a food safe or "
                       "toxic for dogs and cats (leave food out for the full list); first_aid = the pet first-aid kit "
                       "checklist, or steps for a topic like bleeding, choking, heatstroke, poisoning, stings; "
                       "breed_facts = facts and a picture for a dog breed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "food": {"type": "string", "description": "toxic_food: e.g. grapes."},
                "species": {"type": "string", "enum": ["dog", "cat"]},
                "topic": {"type": "string", "description": "first_aid: e.g. heatstroke."},
                "breed": {"type": "string", "description": "breed_facts: e.g. labrador or cocker spaniel."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"pet_guide"}


async def run_tool(name: str, args: dict, settings: Settings, http):
    action = args.get("action")
    if action == "toxic_food":
        return toxic_food(args.get("food"), args.get("species"))
    if action == "first_aid":
        return first_aid(args.get("topic"))
    if action == "breed_facts":
        return await breed_facts(http, args.get("breed"))
    raise ValueError(f"Unknown pet guide action: {action}")
