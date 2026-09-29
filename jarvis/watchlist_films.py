"""Films and TV to watch: a poster-style watchlist, ratings and reviews, tonight's picker, history stats and picks.

Everything lives in watchlist.json (see watchlist_store.py). An item is a film or a show; shows also keep the
season and episode you are on (see watchlist_shows.py).
"""

import random
from collections import Counter, defaultdict

import homestore as hs
import screen
import watchlist_store as ws
from config import Settings

KINDS = ("film", "show")
FAMILY = ("kids", "kid", "children", "child", "family", "son", "daughter")
INSTRUCTION = ("In your reply, suggest three or four similar {what} they have not got yet, one short line each with a "
               "reason. Do not call more tools.")


def kind_of(value, default: str = "film") -> str:
    text = hs.clean(value).lower()
    if text in ("tv", "series", "tv show", "show", "shows"):
        return "show"
    return text if text in KINDS else default


def watch_add(settings: Settings, args: dict) -> str:
    title, kind = hs.need(args.get("title"), "film or show", 120), kind_of(args.get("kind"))
    data = ws.load(settings)
    old = next((i for i in data["items"] if isinstance(i, dict) and i["title"].lower() == title.lower()
                and i["kind"] == kind and i["status"] == "to watch"), None)
    if old is not None:
        return f"{title} is already on your watchlist."
    item = {"title": title, "kind": kind, "status": "to watch", "genre": hs.clean(args.get("genre"), 40).lower(),
            "minutes": ws.minutes_of(args.get("minutes")), "moods": ws.words(args.get("mood")),
            "kids_safe": bool(args.get("kids_safe")), "year": hs.clean(args.get("year"), 4),
            "image": ws.https(args.get("image")), "added": hs.today().isoformat(), "rating": None, "review": "",
            "watched": "", "rewatch": False}
    if kind == "show":
        item.update(season=0, episode=0)
    ws.add_capped(data["items"], item, "watchlist")
    ws.save(settings, data)
    waiting = sum(i.get("status") == "to watch" for i in data["items"])
    return f"Added {title} ({kind}) to your watchlist. {hs.plural(waiting, 'thing')} to watch."


def _tile(item: dict) -> dict:
    sub = " · ".join(x for x in (item.get("genre"), f"{item['minutes']} min" if item.get("minutes") else "") if x)
    badge = "kids" if item.get("kids_safe") else ("show" if item["kind"] == "show" else "")
    return ws.tile(item["title"], sub, badge, ws.stars_of(item.get("rating")), item.get("image", ""),
                   say=f"Tell me about {item['title']} on my watchlist, and mark it watched if I've seen it.")


def watch_list(settings: Settings, args: dict) -> screen.Shown | str:
    kind, genre = hs.clean(args.get("kind")), hs.clean(args.get("genre")).lower()
    items = [i for i in ws.load(settings)["items"] if i.get("status") == "to watch"]
    if kind:
        items = [i for i in items if i["kind"] == kind_of(kind)]
    if genre:
        items = [i for i in items if genre in i.get("genre", "")]
    if args.get("kids_safe"):
        items = [i for i in items if i.get("kids_safe")]
    if not items:
        return "Nothing on your watchlist for that. Say something like 'add Dune to my watchlist'."
    card = ws.board(f"{hs.plural(len(items), 'thing')} on your watchlist, on the screen. " + "; ".join(i["title"] for i in items[:5]) + ".",
                    "Watchlist", "watchlist-list", [ws.gallery([_tile(i) for i in items])],
                    [{"label": "Pick for tonight", "say": "What should we watch tonight?"},
                     {"label": "Add one", "say": "Add something to my watchlist."}])
    return card


def watch_done(settings: Settings, args: dict) -> str:
    data = ws.load(settings)
    title = hs.need(args.get("title"), "film or show", 120)
    kind = hs.clean(args.get("kind"))
    pool = [i for i in data["items"] if isinstance(i, dict) and (not kind or i["kind"] == kind_of(kind))]
    open_items = [i for i in pool if i.get("status") == "to watch"]
    key = hs.find([i["title"] for i in open_items], title) or hs.find([i["title"] for i in pool], title)
    item = next((i for i in open_items + pool if i["title"] == key), None) if key else None
    if item is None:
        item = {"title": title, "kind": kind_of(kind), "status": "to watch", "genre": hs.clean(args.get("genre"), 40).lower(),
                "minutes": 0, "moods": [], "kids_safe": False, "year": "", "image": "", "added": hs.today().isoformat(),
                "rating": None, "review": "", "watched": "", "rewatch": False}
        ws.add_capped(data["items"], item, "watchlist")
    rating = ws.rating_of(args.get("rating"))
    item.update(status="watched", watched=hs.parse_day(args.get("date")).isoformat())
    if rating:
        item["rating"] = rating
    if args.get("review"):
        item["review"] = hs.clean(args.get("review"), 300)
    if args.get("genre") and not item.get("genre"):
        item["genre"] = hs.clean(args.get("genre"), 40).lower()
    ws.save(settings, data)
    count = sum(i.get("status") == "watched" and i.get("watched", "")[:4] == item["watched"][:4] for i in data["items"])
    extra = f", {hs.plural(rating, 'star')}" if rating else ""
    return f"Marked {item['title']} as watched{extra}. That's {hs.plural(count, 'title')} watched this year."


def _watched(settings: Settings) -> list[dict]:
    return [i for i in ws.load(settings)["items"] if isinstance(i, dict) and i.get("status") == "watched"]


def _mood_matches(item: dict, mood: str) -> bool:
    return not mood or any(mood in m.lower() or m.lower() in mood for m in item.get("moods", [])) or mood in item.get("genre", "")


def tonight_pick(settings: Settings, args: dict, pick=random.choice) -> screen.Shown | str:
    mood, top = hs.clean(args.get("mood")).lower(), ws.minutes_of(args.get("max_minutes"))
    who = " ".join(ws.words(args.get("who"), 10)).lower()
    kids = bool(args.get("kids_safe")) or any(w in who.split() or w in who for w in FAMILY)
    kind = hs.clean(args.get("kind"))
    pool = [i for i in ws.load(settings)["items"] if isinstance(i, dict) and i.get("status") == "to watch"]
    if kind:
        pool = [i for i in pool if i["kind"] == kind_of(kind)]
    if kids:
        pool = [i for i in pool if i.get("kids_safe")]
    if top:
        pool = [i for i in pool if not i.get("minutes") or i["minutes"] <= top]
    matches = [i for i in pool if _mood_matches(i, mood)]
    note = ""
    if mood and not matches and pool:
        matches, note = pool, f" Nothing is tagged {mood}, so this ignores the mood."
    if not matches:
        return "Nothing on your watchlist fits that. Try a longer time, another mood, or add more titles."
    chosen = pick(matches)
    others = [i for i in matches if i is not chosen][:5]
    who_text = f" for {', '.join(ws.words(args.get('who'), 10))}" if who else ""
    sections = [ws.gallery([_tile(chosen)], "Tonight's pick")]
    if others:
        sections.append(ws.gallery([_tile(i) for i in others], "Or maybe"))
    return ws.board(f"Tonight{who_text}, how about {chosen['title']}?{note}", "What to watch tonight", "watchlist-tonight",
                    sections, [{"label": "Another pick", "say": "Pick something else for tonight."},
                               {"label": "Plan film night", "say": f"Plan a film night for {chosen['title']}."}])


def history(settings: Settings) -> screen.Shown | str:
    done = _watched(settings)
    if not done:
        return "You haven't marked anything as watched yet."
    by_month = Counter(i["watched"][:7] for i in done if i.get("watched"))
    months = sorted(by_month)[-12:]
    by_genre = Counter(i.get("genre") or "other" for i in done)
    genres = by_genre.most_common(8)
    avg = ws.average(i.get("rating") for i in done)
    sections = [ws.stats([("Watched", str(len(done))), ("Average rating", f"{avg}/5" if avg else "none yet"),
                          ("Films", str(sum(i["kind"] == "film" for i in done))),
                          ("Shows", str(sum(i["kind"] == "show" for i in done)))]),
                ws.chart(months, [by_month[m] for m in months], title="Watched by month"),
                ws.chart([g for g, _ in genres], [n for _, n in genres], title="By genre")]
    text = f"You've watched {len(done)} titles" + (f", averaging {avg} stars" if avg else "") + f". Most watched genre: {genres[0][0]}."
    return ws.board(text, "Watched history", "watchlist-history", sections)


def top_picks(settings: Settings, genre) -> screen.Shown | str:
    genre = hs.clean(genre).lower()
    by = defaultdict(list)
    for i in _watched(settings):
        if i.get("rating") and (not genre or genre in (i.get("genre") or "other")):
            by[i.get("genre") or "other"].append(i)
    if not by:
        return "Rate a few things first, then I can show your top picks."
    rows = []
    for g in sorted(by):
        for i in sorted(by[g], key=lambda x: -x["rating"])[:3]:
            rows.append([g, i["title"], ws.stars_of(i["rating"])])
    best = max((i for v in by.values() for i in v), key=lambda x: x["rating"])
    return ws.board(f"Your top pick{' for ' + genre if genre else ''} is {best['title']}, {best['rating']} stars.",
                    "Top picks by genre", "watchlist-top", [ws.table(["Genre", "Title", "Rating"], rows)])


def _rated(data: dict, kind: str) -> list[tuple]:
    films = [(i["title"], i.get("genre", ""), i["rating"], i["kind"]) for i in data["items"]
             if isinstance(i, dict) and i.get("rating")]
    books = [(b["title"], b.get("genre", ""), b["rating"], "book") for b in data["books"]
             if isinstance(b, dict) and b.get("rating")]
    if kind == "book":
        return books
    return [r for r in films if r[3] == kind] if kind else films + books


def recommend(settings: Settings, kind) -> screen.Shown | str:
    kind = "book" if hs.clean(kind).lower() in ("book", "books") else (kind_of(kind, "") if hs.clean(kind) else "")
    rated = sorted(_rated(ws.load(settings), kind), key=lambda r: -r[2])[:8]
    if not rated:
        return "Rate a few things first (4 or 5 stars for favourites) and I'll recommend more like them."
    listing = "; ".join(f"{t} ({k}{', ' + g if g else ''}, {r} stars)" for t, g, r, k in rated)
    what = {"book": "books", "show": "shows", "film": "films"}.get(kind, "films, shows or books")
    return ws.board(f"Their top rated: {listing}. " + INSTRUCTION.format(what=what), "Your top rated", "watchlist-recommend",
                    [ws.gallery([ws.tile(t, g, k, ws.stars_of(r)) for t, g, r, k in rated])])


def rewatch(settings: Settings, args: dict) -> screen.Shown | str:
    data = ws.load(settings)
    if hs.clean(args.get("title")):
        item = ws.named(data["items"], args.get("title"), "film or show", status="watched")
        item["rewatch"] = True
        ws.save(settings, data)
        return f"Added {item['title']} to your rewatch list."
    items = [i for i in data["items"] if isinstance(i, dict) and i.get("rewatch")]
    if not items:
        return "Your rewatch list is empty. Say 'I want to rewatch Heat' to add something you've already seen."
    return ws.board(f"{hs.plural(len(items), 'title')} to rewatch: " + "; ".join(i["title"] for i in items[:5]) + ".",
                    "Rewatch list", "watchlist-rewatch", [ws.gallery([_tile(i) for i in items])])


def kids_flag(settings: Settings, args: dict) -> str:
    data = ws.load(settings)
    item = ws.named(data["items"], args.get("title"), "film or show")
    item["kids_safe"] = args.get("kids_safe") is not False
    ws.save(settings, data)
    return f"{item['title']} is now marked {'kids-safe' if item['kids_safe'] else 'not for kids'}."


def watch_remove(settings: Settings, args: dict) -> str:
    data = ws.load(settings)
    item = ws.named(data["items"], args.get("title"), "film or show")
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing {item['title']} from the watchlist, then call again with confirmed true."
    data["items"].remove(item)
    ws.save(settings, data)
    return f"Removed {item['title']}."


ACTIONS = ["watch_add", "watch_list", "watch_done", "tonight_pick", "history", "top_picks", "recommend", "rewatch",
           "kids_flag", "watch_remove"]


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "watchlist",
        "description": "Films and TV watchlist. watch_add (title, kind film or show, genre, minutes, mood, kids_safe), "
                       "watch_list shows poster tiles (filter kind, genre, kids_safe), watch_done (title, rating 1-5, "
                       "review one line, date). tonight_pick answers 'what should we watch tonight' (mood, max_minutes, "
                       "who is watching; kids means kids-safe only). history shows watched stats by month, genre and "
                       "average rating. top_picks (genre) from their own ratings. recommend (kind film, show or book) "
                       "returns their top rated so you suggest similar ones. rewatch (title adds; no title lists). "
                       "kids_flag (title, kids_safe). watch_remove (confirmed true only after the user agrees).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "title": text, "kind": {"type": "string", "enum": ["film", "show", "book"]}, "genre": text,
                "minutes": {"type": "integer", "description": "Length of the film or an episode."},
                "max_minutes": {"type": "integer", "description": "Longest they want to watch tonight."},
                "mood": text, "who": {"type": "array", "items": text, "description": "Who is watching."},
                "kids_safe": {"type": "boolean"}, "year": text, "image": {"type": "string", "description": "https poster link."},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5}, "review": text,
                "date": {"type": "string", "description": "YYYY-MM-DD, default today."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"watchlist"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    actions = {
        "watch_add": lambda: watch_add(settings, args),
        "watch_list": lambda: watch_list(settings, args),
        "watch_done": lambda: watch_done(settings, args),
        "tonight_pick": lambda: tonight_pick(settings, args),
        "history": lambda: history(settings),
        "top_picks": lambda: top_picks(settings, a("genre")),
        "recommend": lambda: recommend(settings, a("kind")),
        "rewatch": lambda: rewatch(settings, args),
        "kids_flag": lambda: kids_flag(settings, args),
        "watch_remove": lambda: watch_remove(settings, args),
    }
    if a("action") not in actions:
        raise ValueError("Unknown watchlist action.")
    return actions[a("action")]()
