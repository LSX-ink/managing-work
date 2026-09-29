"""Books: a reading list with page progress, finished books and a yearly goal ring, a reading streak, notes and quotes,
and a series order helper that searches Open Library (keyless; only the series or author words are sent).

Books live in watchlist.json; pages read each day go in its reading_log so the streak can be counted.
"""

import random
from datetime import date, timedelta

import httpx

import feeds
import homestore as hs
import screen
import watchlist_store as ws
from config import Settings

OPEN_LIBRARY = "https://openlibrary.org/search.json"
MAX_LOG_DAYS = 800
MAX_NOTES = 200
ACTIONS = ["book_add", "book_progress", "book_finish", "reading_now", "goal_set", "goal_show", "log_reading",
           "reading_streak", "book_note", "book_quote", "notes_show", "series_order"]


def _by(book: dict) -> str:
    return f"{book['title']} by {book['author']}" if book.get("author") else book["title"]


def _new(title, author="", pages=0, genre="", series="", kids_safe=False) -> dict:
    return {"title": hs.need(title, "book", 120), "author": hs.clean(author, 80), "pages": ws.minutes_of(pages),
            "page": 0, "genre": hs.clean(genre, 40).lower(), "series": hs.clean(series, 80), "kids_safe": bool(kids_safe),
            "status": "to read", "rating": None, "review": "", "started": "", "finished": "", "notes": [], "quotes": []}


def _find(data: dict, title, create: bool = False, **fields) -> dict:
    """The book called title; with create, add it to the list if it isn't there."""
    books = data["books"]
    key = hs.find([b["title"] for b in books if isinstance(b, dict)], hs.need(title, "book", 120))
    book = next((b for b in books if isinstance(b, dict) and b["title"] == key), None) if key else None
    if book is None:
        if not create:
            raise ValueError(f"I can't find a book called {hs.clean(title)} on your list.")
        book = _new(title, **fields)
        ws.add_capped(books, book, "reading")
    return book


def _log(data: dict, day: date, pages: int) -> None:
    log = data["reading_log"]
    log[day.isoformat()] = int(log.get(day.isoformat(), 0)) + pages
    for old in sorted(log)[:-MAX_LOG_DAYS]:
        del log[old]


def book_add(settings: Settings, args: dict) -> str:
    data = ws.load(settings)
    title = hs.need(args.get("title"), "book", 120)
    if any(isinstance(b, dict) and b["title"].lower() == title.lower() for b in data["books"]):
        return f"{title} is already on your reading list."
    book = _new(title, args.get("author"), args.get("pages"), args.get("genre"), args.get("series"), args.get("kids_safe"))
    ws.add_capped(data["books"], book, "reading")
    ws.save(settings, data)
    return f"Added {_by(book)} to your reading list. {hs.plural(sum(b.get('status') == 'to read' for b in data['books']), 'book')} waiting."


def _bar(book: dict) -> dict:
    top = book.get("pages") or 0
    note = f"page {book['page']} of {top}" if top else f"page {book['page']}"
    if top:
        note += f" ({min(100, round(book['page'] * 100 / top))}%)"
    return ws.meter(book["title"], book["page"], top or max(book["page"], 1), note)


def book_progress(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    book = _find(data, args.get("title"), create=True, author=args.get("author"), pages=args.get("pages"))
    if args.get("pages") and not book.get("pages"):
        book["pages"] = ws.minutes_of(args.get("pages"))
    page = int(hs.number(args.get("page"), "page number", 0, 20000))
    if book.get("pages") and page > book["pages"]:
        raise ValueError(f"{book['title']} only has {book['pages']} pages.")
    today = hs.today()
    _log(data, today, max(0, page - book.get("page", 0)))
    book.update(page=page, status="reading", started=book.get("started") or today.isoformat())
    ws.save(settings, data)
    left = f", {book['pages'] - page} to go" if book.get("pages") else ""
    return ws.board(f"You're on page {page} of {book['title']}{left}.", "Reading progress", "watchlist-progress",
                    [ws.section("meters", "Now reading", rows=[_bar(book)])],
                    [{"label": "Finished it", "say": f"I finished {book['title']}."}])


def book_finish(settings: Settings, args: dict) -> str:
    data = ws.load(settings)
    book = _find(data, args.get("title"), create=True, author=args.get("author"))
    day = hs.parse_day(args.get("date"))
    rating = ws.rating_of(args.get("rating"))
    if book.get("pages"):
        _log(data, day, max(0, book["pages"] - book.get("page", 0)))
        book["page"] = book["pages"]
    book.update(status="finished", finished=day.isoformat())
    if rating:
        book["rating"] = rating
    if args.get("review"):
        book["review"] = hs.clean(args.get("review"), 300)
    ws.save(settings, data)
    count = sum(isinstance(b, dict) and b.get("finished", "")[:4] == str(day.year) for b in data["books"])
    goal = data["goal"].get(str(day.year))
    extra = f", {hs.plural(rating, 'star')}" if rating else ""
    of = f" of your {goal} goal" if goal else ""
    return f"Finished {_by(book)}{extra}. That's {hs.plural(count, 'book')} this year{of}."


def reading_now(settings: Settings) -> screen.Shown | str:
    books = [b for b in ws.load(settings)["books"] if isinstance(b, dict) and b.get("status") == "reading"]
    if not books:
        return "You're not reading anything right now. Say 'I'm on page 40 of Dune' to start tracking."
    return ws.board("Reading now: " + "; ".join(f"{b['title']} at page {b['page']}" for b in books) + ".", "Reading now",
                    "watchlist-reading", [ws.section("meters", "Progress", rows=[_bar(b) for b in books])])


def goal_set(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    year = str(ws.minutes_of(args.get("year")) or hs.today().year)
    data["goal"][year] = int(hs.number(args.get("goal"), "books goal", 1, 1000))
    ws.save(settings, data)
    return goal_show(settings, f"Your {year} reading goal is {data['goal'][year]} books.")


def goal_show(settings: Settings, said: str = "") -> screen.Shown | str:
    data, today = ws.load(settings), hs.today()
    year = str(today.year)
    done = [b for b in data["books"] if isinstance(b, dict) and b.get("finished", "")[:4] == year]
    goal = data["goal"].get(year)
    if not goal:
        return "You haven't set a reading goal for this year. Say 'my reading goal is 24 books'."
    expected = goal * today.timetuple().tm_yday / 365
    pace = "ahead of" if len(done) > expected + 0.5 else ("behind" if len(done) < expected - 0.5 else "right on")
    said = said or f"You've finished {len(done)} of {goal} books this year, {pace} pace."
    sections = [ws.section("ring", "", value=len(done), max=goal, label=f"Books in {year}", note=f"{pace} pace")]
    if done:
        sections.append(ws.lines([(f"{_by(b)} {ws.stars_of(b.get('rating'))}".strip(), f"Tell me about my notes on {b['title']}.")
                                  for b in sorted(done, key=lambda b: b["finished"])], "Finished this year"))
    return ws.board(said, "Reading goal", "watchlist-goal", sections)


def log_reading(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    pages = int(hs.number(args.get("pages"), "pages", 1, 5000))
    day = hs.parse_day(args.get("date"))
    _log(data, day, pages)
    ws.save(settings, data)
    return reading_streak(settings, f"Logged {hs.plural(pages, 'page')}.")


def _streaks(log: dict, today: date) -> tuple[int, int]:
    days = sorted(date.fromisoformat(d) for d, n in log.items() if n)
    longest = run = 0
    prev = None
    for d in days:
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        longest, prev = max(longest, run), d
    day = today if today in days else today - timedelta(days=1)
    current = 0
    while day in days:
        current, day = current + 1, day - timedelta(days=1)
    return current, longest


def reading_streak(settings: Settings, said: str = "") -> screen.Shown | str:
    data, today = ws.load(settings), hs.today()
    log = {d: n for d, n in data["reading_log"].items() if isinstance(n, int)}
    if not log:
        return "No reading logged yet. Say 'I read 20 pages today' to start a streak."
    current, longest = _streaks(log, today)
    last = [(today - timedelta(days=i)) for i in range(13, -1, -1)]
    said = (said + " " if said else "") + f"Reading streak: {hs.plural(current, 'day')}. Your longest is {longest}."
    sections = [ws.stats([("Streak", hs.plural(current, "day")), ("Longest", hs.plural(longest, "day")),
                          ("Pages this week", str(sum(log.get((today - timedelta(days=i)).isoformat(), 0) for i in range(7))))]),
                ws.chart([d.strftime("%d %b") for d in last], [log.get(d.isoformat(), 0) for d in last], title="Pages, last 14 days")]
    return ws.board(said, "Reading streak", "watchlist-streak", sections)


def _entry(settings: Settings, args: dict, field: str, what: str) -> str:
    data = ws.load(settings)
    book = _find(data, args.get("title"))
    text = hs.need(args.get("text"), what, 500)
    if len(book[field]) >= MAX_NOTES:
        raise ValueError(f"That book has too many {field}.")
    book[field].append({"text": text, "page": ws.minutes_of(args.get("page")), "date": hs.today().isoformat()})
    ws.save(settings, data)
    return f"Saved that {what} for {book['title']}. It has {hs.plural(len(book[field]), what)}."


def book_note(settings: Settings, args: dict) -> str:
    return _entry(settings, args, "notes", "note")


def book_quote(settings: Settings, args: dict) -> str:
    return _entry(settings, args, "quotes", "quote")


def _page(entry: dict) -> str:
    return f" (p. {entry['page']})" if entry.get("page") else ""


def notes_show(settings: Settings, args: dict, pick=random.choice) -> screen.Shown | str:
    data = ws.load(settings)
    if not hs.clean(args.get("title")):
        every = [(b["title"], q) for b in data["books"] if isinstance(b, dict) for q in b["quotes"]]
        if not every:
            return "No book quotes saved yet. Say 'save this quote from Dune: ...'."
        title, quote = pick(every)
        return ws.board(f"\"{quote['text']}\" from {title}.", "A favourite quote", "watchlist-quote",
                        [ws.section("text", "", text=f"\"{quote['text']}\"\n{title}")],
                        [{"label": "Another", "say": "Read me another favourite book quote."}])
    book = _find(data, args.get("title"))
    if not book["notes"] and not book["quotes"]:
        return f"No notes or quotes for {book['title']} yet."
    sections = []
    if book["notes"]:
        sections.append(ws.lines([f"{n['text']}{_page(n)}" for n in book["notes"]], "Notes"))
    if book["quotes"]:
        sections.append(ws.lines([f"\"{q['text']}\"{_page(q)}" for q in book["quotes"]], "Quotes"))
    return ws.board(f"{book['title']} has {hs.plural(len(book['notes']), 'note')} and {hs.plural(len(book['quotes']), 'quote')}.",
                    f"Notes: {book['title']}", "watchlist-notes", sections)


async def series_order(http: httpx.AsyncClient, query) -> screen.Shown:
    query = hs.need(query, "series or author", 100)
    body = await feeds.fetch_json(http, OPEN_LIBRARY, "Open Library", {
        "q": query, "limit": 40, "fields": "title,author_name,first_publish_year"})
    seen, rows = set(), []
    for doc in sorted((d for d in (body.get("docs") or []) if isinstance(d, dict) and d.get("title")),
                      key=lambda d: d.get("first_publish_year") or 9999):
        key = hs.clean(doc["title"], 120).lower()
        if key not in seen:
            seen.add(key)
            rows.append([str(len(rows) + 1), hs.clean(doc["title"], 120), hs.clean(", ".join((doc.get("author_name") or [])[:1]), 60),
                         str(doc.get("first_publish_year") or "")])
    if not rows:
        raise ValueError(f"Open Library found no books for {query}.")
    rows = rows[:20]
    return ws.board(f"Here are {len(rows)} books for {query} in order of first publication, starting with {rows[0][1]}. "
                    "Open Library search isn't a perfect series list, so mention any you know are missing or out of order.",
                    f"Reading order: {query}", "watchlist-series", [ws.table(["#", "Title", "Author", "Year"], rows)],
                    [{"label": "Add first to list", "say": f"Add the book {rows[0][1]} to my reading list."}])


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "watch_books",
        "description": "Reading list with progress, goal, streak, notes and series order. book_add (title, author, pages, "
                       "genre, series, kids_safe). book_progress (title, page = page they are on) shows a progress bar. "
                       "book_finish (title, rating 1-5, review). reading_now shows bars. goal_set (goal books, year) "
                       "and goal_show (ring of books finished this year). log_reading (pages read today) and "
                       "reading_streak. book_note and book_quote (title, text, page); notes_show (title; no title = a "
                       "random favourite quote). series_order (query = series name or author) lists books in order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "title": text, "author": text, "genre": text, "series": text, "query": text, "text": text, "review": text,
                "pages": {"type": "integer", "description": "Total pages of the book, or pages read for log_reading."},
                "page": {"type": "integer", "description": "The page they are on, or the page of a note or quote."},
                "goal": {"type": "integer"}, "year": {"type": "integer"}, "kids_safe": {"type": "boolean"},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                "date": {"type": "string", "description": "YYYY-MM-DD, default today."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"watch_books"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    a = args.get("action")
    if a == "series_order":
        return await series_order(http, args.get("query") or args.get("title") or args.get("series"))
    actions = {
        "book_add": lambda: book_add(settings, args),
        "book_progress": lambda: book_progress(settings, args),
        "book_finish": lambda: book_finish(settings, args),
        "reading_now": lambda: reading_now(settings),
        "goal_set": lambda: goal_set(settings, args),
        "goal_show": lambda: goal_show(settings),
        "log_reading": lambda: log_reading(settings, args),
        "reading_streak": lambda: reading_streak(settings),
        "book_note": lambda: book_note(settings, args),
        "book_quote": lambda: book_quote(settings, args),
        "notes_show": lambda: notes_show(settings, args),
    }
    if a not in actions:
        raise ValueError("Unknown book action.")
    return actions[a]()
