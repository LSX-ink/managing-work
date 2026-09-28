"""Kids' fun: bedtime story plans, activity ideas, clean jokes and tongue twisters, and a big-button drawing pad.

All lists are built in (kids_lists.py); nothing goes online. The story helper picks the parts and gives Alfred a
plan to tell the story from, and saves each story's title in kids-stories.json. Jokes and tongue twisters don't
repeat until every one has been heard (kids-fun.json). The drawing pad (frontend/popup-kids.js) saves pictures
into a memory folder through the page's own /memory endpoints.
"""

import random

import homestore as hs
import memory
import screen
from config import Settings
from kids_lists import (
    ACTIVITIES,
    JOKES,
    STORY_HEROES,
    STORY_OBJECTS,
    STORY_PLACES,
    STORY_SIDEKICKS,
    STORY_THEMES,
    STORY_TWISTS,
    TONGUE_TWISTERS,
)

STORIES, SEEN = "kids-stories.json", "kids-fun.json"
screen.EXTRA_KINDS.add("kids-draw")
SETTINGS_ = ("indoor", "outdoor", "rainy", "any")
MAX_STORIES = 200


def _next(settings: Settings, which: str, size: int) -> int:
    """A random index not used since the whole list was last heard."""
    found = hs.load(settings, SEEN, {})
    seen = [i for i in found.get(which, []) if isinstance(i, int) and 0 <= i < size]
    left = [i for i in range(size) if i not in seen] or list(range(size))
    pick = random.choice(left)
    found[which] = (seen if len(left) < size else []) + [pick]
    hs.save(settings, SEEN, found)
    return pick


# Bedtime stories

def _choose(value, options: list[str]) -> str:
    return hs.clean(value, 60) or random.choice(options)


def story(settings: Settings, characters, place, theme, name) -> screen.Shown:
    chars = [hs.clean(c, 60) for c in characters or [] if hs.clean(c)]
    kid = hs.clean(name, 30)
    hero = chars[0] if chars else (f"{kid}, a brave explorer" if kid else random.choice(STORY_HEROES))
    sidekick = chars[1] if len(chars) > 1 else random.choice(STORY_SIDEKICKS)
    where = _choose(place, STORY_PLACES)
    wanted = hs.clean(theme).lower()
    key = hs.find(STORY_THEMES, wanted) if wanted else random.choice(list(STORY_THEMES))
    problem, lesson = STORY_THEMES[key] if key else (f"a problem about {wanted}", f"something about {wanted}")
    thing, twist = random.choice(STORY_OBJECTS), random.choice(STORY_TWISTS)
    short = hero.split(",")[0].removeprefix("a ").removeprefix("an ").strip()
    title = random.choice(["{h} and {o}", "{h} in {p}", "The Night {h} Found {o}"]).format(
        h=short[:1].upper() + short[1:], o=thing.removeprefix("a ").removeprefix("an ").title(),
        p=where.removeprefix("an ").removeprefix("a ").removeprefix("the ").title())
    plan = [("Title", title), ("Hero", hero), ("Friend", sidekick), ("Place", where), ("Theme", key or wanted),
            ("Problem", problem), ("Magic thing", thing), ("Twist", twist), ("Lesson", lesson)]
    saved = hs.load(settings, STORIES, [])
    saved = (saved + [{"date": hs.today().isoformat(), "title": title, "child": kid}])[-MAX_STORIES:]
    hs.save(settings, STORIES, saved)
    outline = "\n".join(f"{a}: {b}" for a, b in plan)
    card = screen.card("text", title, "kids-story", text=outline,
                       buttons=[{"label": "Another story", "say": "Make up another bedtime story."},
                                {"label": "Stories told", "say": "Which bedtime stories have we had?"}])
    brief = ("Tell this now as a gentle bedtime story of about three minutes, in simple words, with a calm, happy "
             f"ending and nothing scary{', using ' + kid + ' as the name of the hero' if kid else ''}. Plan:\n")
    return screen.Shown(brief + outline, card)


def stories(settings: Settings) -> screen.Shown:
    saved = [s for s in hs.load(settings, STORIES, []) if isinstance(s, dict)]
    if not saved:
        raise ValueError("No bedtime stories yet. Ask me to make one up.")
    rows = [[s["date"], s["title"], s.get("child", "")] for s in reversed(saved[-50:])]
    card = screen.card("table", "Bedtime stories told", "kids-stories", columns=["Date", "Title", "For"], rows=rows)
    return screen.Shown(f"{hs.plural(len(saved), 'story', 'stories')} so far; the last was {saved[-1]['title']}.", card)


# Activity ideas

def _matches(setting: str, free: bool, age) -> list[int]:
    out = []
    for i, (_, where, rainy, costs_nothing, young, old) in enumerate(ACTIVITIES):
        if setting == "rainy" and not rainy or setting in ("indoor", "outdoor") and where != setting:
            continue
        if free and not costs_nothing or age is not None and not young <= age <= old:
            continue
        out.append(i)
    return out


def activity(settings: Settings, setting, free, age, show_all) -> screen.Shown:
    setting = setting if setting in SETTINGS_ else "any"
    years = int(hs.number(age, "age", 0, 18)) if age is not None else None
    found = _matches(setting, bool(free), years)
    if not found:
        raise ValueError("I haven't got an idea that fits all of that; try fewer conditions.")
    words = " ".join(w for w in ["free" if free else "", "" if setting == "any" else setting] if w)
    if show_all:
        card = screen.card("list", f"{words.title() or 'All'} activity ideas", "kids-activities",
                           items=[{"label": ACTIVITIES[i][0]} for i in found])
        return screen.Shown(f"{hs.plural(len(found), 'idea')} on the screen.", card)
    pick = ACTIVITIES[found[_next(settings, f"activity-{setting}-{free}-{years}", len(found))]]
    tags = [pick[1], "good when it rains" if pick[2] else "", "costs nothing" if pick[3] else "",
            f"ages {pick[4]} to {pick[5]}"]
    sort = f"{words} " if words else ""
    again = f"Give me another {sort}activity idea for the kids" + (f" aged {years}." if years is not None else ".")
    text = f"{pick[0]}\n\n" + " · ".join(t for t in tags if t)
    card = screen.card("text", "Let's do this!", "kids-activity", text=text,
                       buttons=[{"label": "Another idea", "say": again},
                                {"label": "Show all", "say": f"Show all the {sort}activity ideas."}])
    return screen.Shown(f"How about this: {pick[0]}.", card)


# Jokes and tongue twisters

def joke(settings: Settings) -> screen.Shown:
    q, a = JOKES[_next(settings, "jokes", len(JOKES))]
    card = screen.card("text", "Joke time!", "kids-joke", text=f"{q}\n\n{a}",
                       buttons=[{"label": "Another joke", "say": "Tell the kids another joke."}])
    return screen.Shown(f"{q} ... {a}", card)


def tongue_twister(settings: Settings) -> screen.Shown:
    t = TONGUE_TWISTERS[_next(settings, "twisters", len(TONGUE_TWISTERS))]
    card = screen.card("text", "Say it three times fast!", "kids-twister", text=t,
                       buttons=[{"label": "Another one", "say": "Give us another tongue twister."}])
    return screen.Shown(f"Try saying this three times fast: {t}", card)


# Drawing pad

def drawing_pad(settings: Settings, folder, name) -> screen.Shown:
    wanted = (hs.clean(folder) or "Ideas").lower()
    names = memory.names(settings)
    match = next((n for n in names if n.lower() == wanted), None)
    if not match:
        raise ValueError(f"I can only save drawings into one of these folders: {', '.join(names)}.")
    kid = hs.clean(name, 30)
    card = screen.card("kids-draw", f"{kid}'s drawing pad" if kid else "Drawing pad", "kids-draw",
                       data={"folder": match, "child": kid})
    return screen.Shown("Here's the drawing pad. Have fun!", card)


# The tool

ACTIONS = ("bedtime_story", "stories_told", "activity_idea", "kids_joke", "tongue_twister", "drawing_pad")


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "kids_fun",
        "description": "Fun for children. action: 'bedtime_story' make up a bedtime story: picks characters, "
                       "place and theme (friendship, bravery, kindness, sharing, adventure, trying again, honesty, "
                       "helping, calm) and returns a plan for you to tell it from; 'stories_told' saved story "
                       "titles; 'activity_idea' something to do with the kids (setting indoor/outdoor/rainy, "
                       "free = costs nothing, age; show_all lists every match); 'kids_joke' a clean joke for "
                       "children; 'tongue_twister'; 'drawing_pad' a big-button colouring and drawing pad with "
                       "stamps that saves the picture to a folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "child": {"type": "string", "description": "The child's first name."},
                "characters": {"type": "array", "items": text},
                "place": text,
                "theme": text,
                "setting": {"type": "string", "enum": list(SETTINGS_)},
                "free": {"type": "boolean"},
                "age": {"type": "integer"},
                "show_all": {"type": "boolean"},
                "folder": {"type": "string", "description": "Memory folder to save drawings in, e.g. Ideas."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"kids_fun"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    actions = {
        "bedtime_story": lambda: story(settings, a("characters"), a("place"), a("theme"), a("child")),
        "stories_told": lambda: stories(settings),
        "activity_idea": lambda: activity(settings, a("setting"), a("free"), a("age"), bool(a("show_all"))),
        "kids_joke": lambda: joke(settings),
        "tongue_twister": lambda: tongue_twister(settings),
        "drawing_pad": lambda: drawing_pad(settings, a("folder"), a("child")),
    }
    if a("action") not in actions:
        raise ValueError(f"I can't do {a('action')} with kids' fun.")
    return actions[a("action")]()
