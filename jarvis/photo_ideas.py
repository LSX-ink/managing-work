"""Photography ideas and learning: composition tips with a drawn grid example, a photo challenge of the day,
photo-walk ideas, starting camera settings for common scenes and a glossary.

Composition tips pop up a picture with the guide lines drawn over it (kind "photo-grid", frontend/popup-photo.js).
Everything is built in; nothing is saved or fetched.
"""

import random

import homestore as hs
import photo_data
import photo_store as ps
import screen
from config import Settings

screen.EXTRA_KINDS.add("photo-grid")
ACTIONS = ("composition", "composition_list", "challenge", "challenge_random", "walk", "settings", "term")
WALK_STEPS = 6


def _tip_key(value) -> str:
    text = hs.clean(value).lower().replace(" ", "-")
    if text in photo_data.COMPOSITION:
        return text
    hits = [k for k in photo_data.COMPOSITION if text and (text in k or text in photo_data.COMPOSITION[k][0].lower())]
    if len(hits) == 1:
        return hits[0]
    raise ValueError("Which composition tip? Try rule of thirds, leading lines, symmetry, framing, diagonals, "
                     "golden ratio, negative space, fill the frame, layers, odd numbers or patterns.")


def composition(tip) -> screen.Shown:
    key = _tip_key(tip)
    name, how, advice, overlay = photo_data.COMPOSITION[key]
    card = screen.card("photo-grid", name, f"photo-grid-{key}", data={"overlay": overlay, "name": name, "how": how, "tip": advice},
                       buttons=[{"label": "Next tip", "say": "Show me another composition tip."}])
    return screen.Shown(f"{name}: {how}", card)


def composition_list() -> screen.Shown:
    items = [{"label": v[0], "say": f"Show me the {v[0]} composition tip."} for v in photo_data.COMPOSITION.values()]
    card = screen.card("list", "Composition tips", "photo-composition", items=items)
    return screen.Shown("Tap a composition tip to see it drawn on a picture.", card)


def _challenge(prompt: str, heading: str, rng: random.Random) -> screen.Shown:
    tip = rng.choice(photo_data.CHALLENGE_TIPS)
    card = screen.card("text", heading, "photo-challenge", text=f"{prompt}\n\nTip: {tip}",
                       buttons=[{"label": "Another one", "say": "Give me a random photo challenge."},
                                {"label": "Done", "say": "Log today's photo for my photo project."}])
    return screen.Shown(f"{heading}: {prompt}.", card)


def challenge() -> screen.Shown:
    day = hs.today()
    prompt = photo_data.CHALLENGES[day.toordinal() % len(photo_data.CHALLENGES)]
    return _challenge(prompt, "Photo challenge of the day", random.Random(day.toordinal()))


def challenge_random() -> screen.Shown:
    rng = random.Random()
    return _challenge(rng.choice(photo_data.CHALLENGES), "Random photo challenge", rng)


def walk(place, minutes) -> screen.Shown:
    place = hs.clean(place).lower() or "town"
    if place not in photo_data.WALK_PLACES:
        raise ValueError(f"I have walk ideas for: {', '.join(photo_data.WALK_PLACES)}.")
    length = int(hs.number(minutes or 45, "minutes", 10, 480))
    rng = random.Random()
    theme = rng.choice(photo_data.WALK_THEMES)
    items = [f"Theme: look for {theme}", f"Rule: {rng.choice(photo_data.WALK_RULES)}",
             f"Route: {rng.choice(photo_data.WALK_PLACES[place])}", f"Bonus: {rng.choice(photo_data.WALK_BONUS)}",
             "Warm up: take three photos in the first five minutes",
             f"Finish: keep your favourite and delete the rest within {length} minutes"]
    card = screen.card("list", f"Photo walk: {place}, {length} min", "photo-walk", checks=True,
                       items=[{"label": i} for i in items[:WALK_STEPS]],
                       buttons=[{"label": "Another walk", "say": f"Give me another photo walk idea for a {place}."}])
    return screen.Shown(f"A {length} minute {place} walk: look for {theme}.", card)


def settings_help(scene) -> screen.Shown:
    scene = hs.clean(scene).lower().replace(" ", "-")
    if scene and scene not in photo_data.SETTINGS:
        raise ValueError(f"I have starting settings for: {', '.join(photo_data.SETTINGS)}.")
    if not scene:
        rows = [[k, v[0], v[1], v[2]] for k, v in photo_data.SETTINGS.items()]
        return screen.Shown("Starting settings for common scenes.",
                            ps.table("Camera settings", ["Scene", "Aperture", "Shutter", "ISO"], rows, "photo-settings"))
    ap, sh, iso, focus, note = photo_data.SETTINGS[scene]
    rows = [["Aperture", ap], ["Shutter", sh], ["ISO", iso], ["Focus", focus], ["Why", note]]
    return screen.Shown(f"For {scene.replace('-', ' ')}: {ap}, {sh}, ISO {iso}.",
                        ps.table(f"Settings for {scene.replace('-', ' ')}", ["", "Suggestion"], rows, f"photo-settings-{scene}"))


def term(word) -> screen.Shown:
    text = hs.clean(word).lower()
    if not text:
        items = [{"label": k, "say": f"What does {k} mean in photography?"} for k in photo_data.GLOSSARY]
        return screen.Shown("Tap a word for its meaning.", screen.card("list", "Photography words", "photo-terms", items=items))
    hits = [k for k in photo_data.GLOSSARY if k == text] or [k for k in photo_data.GLOSSARY if text in k or k in text]
    if not hits:
        raise ValueError("I don't have that word in my photography glossary.")
    k = hits[0]
    return screen.Shown(f"{k}: {photo_data.GLOSSARY[k]}", screen.card("text", k.title(), f"photo-term-{k}", text=photo_data.GLOSSARY[k]))


def tool_definitions() -> list[dict]:
    return [{
        "name": "photo_ideas",
        "description": "Photography ideas and learning. composition (a tip like rule of thirds, leading lines, symmetry, "
                       "framing, golden ratio, negative space drawn on a picture), composition_list, challenge (photo "
                       "challenge of the day), challenge_random, walk (photo-walk idea: place town, park, seaside, "
                       "countryside or home, minutes), settings (starting camera settings for a scene such as portrait, "
                       "stars, waterfall), term (what a photo word like bokeh or aperture means).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "tip": {"type": "string"}, "place": {"type": "string", "enum": list(photo_data.WALK_PLACES)},
                "minutes": {"type": "integer"}, "scene": {"type": "string", "enum": list(photo_data.SETTINGS)},
                "word": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"photo_ideas"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    table = {
        "composition": lambda: composition(a("tip")),
        "composition_list": composition_list,
        "challenge": challenge,
        "challenge_random": challenge_random,
        "walk": lambda: walk(a("place"), a("minutes")),
        "settings": lambda: settings_help(a("scene")),
        "term": lambda: term(a("word")),
    }
    if a("action") not in table:
        raise ValueError(f"I can't do {a('action')}. Try: {', '.join(ACTIONS)}.")
    return table[a("action")]()
