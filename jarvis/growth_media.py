"""Reading and watching: a reading list with ratings, a watch list with a random pick for tonight, saved links
by tag, and favourite quotes.

Kept in growth-books.json, growth-watch.json, growth-bookmarks.json and growth-quotes.json in the memory folder.
Links are only stored here; opening one uses the same http(s) check as open_url.
"""

import random
import webbrowser
from datetime import date

import growth_store as store
from config import Settings

MAX_ITEMS = 2000


def _add_capped(items: list, item: dict, what: str) -> None:
    if len(items) >= MAX_ITEMS:
        raise ValueError(f"The {what} is full.")
    items.append(item)


def _book(books: list[dict], title: str, author: str = "") -> dict:
    title = store.need(title, "book", 120)
    book = store.find(books, "title", title)
    if book is None:
        book = {"title": title, "author": store.clean(author, 80), "status": "to read", "rating": None,
                "finished": None}
        _add_capped(books, book, "reading list")
    elif author and not book["author"]:
        book["author"] = store.clean(author, 80)
    return book


def _by(book: dict) -> str:
    return f"{book['title']} by {book['author']}" if book["author"] else book["title"]


def book_add(settings: Settings, title: str, author: str) -> str:
    books = store.load(settings, "books", [])
    before = len(books)
    book = _book(books, title, author)
    store.save(settings, "books", books)
    waiting = sum(b["status"] == "to read" for b in books)
    return (f"Added {_by(book)} to your reading list." if len(books) > before else f"{_by(book)} is already on it.") \
        + f" {store.plural(waiting, 'book')} waiting."


def book_reading(settings: Settings, title: str, author: str) -> str:
    books = store.load(settings, "books", [])
    book = _book(books, title, author)
    book["status"] = "reading"
    store.save(settings, "books", books)
    return f"Now reading {_by(book)}. Enjoy it."


def book_finished(settings: Settings, title: str, author: str, rating, today: date) -> str:
    books = store.load(settings, "books", [])
    book = _book(books, title, author)
    if rating is not None:
        rating = int(store.number(rating, "rating"))
        if not 1 <= rating <= 5:
            raise ValueError("Rate it from 1 to 5 stars.")
    book.update(status="finished", rating=rating, finished=today.isoformat())
    store.save(settings, "books", books)
    count = sum((b.get("finished") or "")[:4] == str(today.year) for b in books)
    stars = f", {store.plural(rating, 'star')}" if rating else ""
    return f"Finished {_by(book)}{stars}. That's {store.plural(count, 'book')} this year."


def reading_now(settings: Settings) -> str:
    books = store.load(settings, "books", [])
    now = [_by(b) for b in books if b["status"] == "reading"]
    waiting = [_by(b) for b in books if b["status"] == "to read"]
    head = f"Reading now: {'; '.join(now)}." if now else "You're not reading anything right now."
    return head + (f"\nNext on the list ({len(waiting)}): {'; '.join(waiting[:10])}." if waiting else "")


def finished_this_year(settings: Settings, today: date) -> str:
    done = [b for b in store.load(settings, "books", []) if (b.get("finished") or "")[:4] == str(today.year)]
    if not done:
        return f"No books finished yet in {today.year}."
    lines = "\n".join(f"- {_by(b)}" + (f", {b['rating']}/5" if b.get("rating") else "") for b in done)
    return f"{store.plural(len(done), 'book')} finished in {today.year}:\n{lines}"


def watch_add(settings: Settings, title: str, kind: str) -> str:
    title = store.need(title, "film or series", 120)
    items = store.load(settings, "watch", [])
    if any(i["title"].lower() == title.lower() and not i["watched"] for i in items):
        return f"{title} is already on your watch list."
    _add_capped(items, {"title": title, "kind": kind if kind in ("film", "series") else "film", "watched": None},
                "watch list")
    store.save(settings, "watch", items)
    return f"Added {title} to your watch list. {store.plural(sum(not i['watched'] for i in items), 'thing')} to watch."


def watched(settings: Settings, title: str, today: date) -> str:
    items = store.load(settings, "watch", [])
    item = store.find([i for i in items if not i["watched"]], "title", title)
    if item is None:
        return "That isn't on your watch list."
    item["watched"] = today.isoformat()
    store.save(settings, "watch", items)
    return f"Marked {item['title']} as watched."


def watch_list(settings: Settings, kind: str) -> str:
    items = [i for i in store.load(settings, "watch", []) if not i["watched"] and (not kind or i["kind"] == kind)]
    if not items:
        return "Your watch list is empty."
    return f"To watch ({len(items)}):\n" + "\n".join(f"- {i['title']} ({i['kind']})" for i in items)


def watch_pick(settings: Settings, kind: str, pick=random.choice) -> str:
    items = [i for i in store.load(settings, "watch", []) if not i["watched"] and (not kind or i["kind"] == kind)]
    if not items:
        return "Nothing on your watch list to pick from."
    item = pick(items)
    return f"Tonight's pick: {item['title']} ({item['kind']})."


def _safe_url(url: str) -> bool:
    import tools  # lazily: tools imports this module

    return tools.is_safe_url(url)


def bookmark_save(settings: Settings, url: str, title: str, tag: str, today: date) -> str:
    url = store.clean(url, 2000)
    if not _safe_url(url):
        raise ValueError("I can only save http or https links.")
    marks = store.load(settings, "bookmarks", [])
    title = store.clean(title, 120) or url
    tag = store.clean(tag, 40).lower() or "general"
    marks = [m for m in marks if m["url"] != url]
    _add_capped(marks, {"url": url, "title": title, "tag": tag, "saved": today.isoformat()}, "bookmark list")
    store.save(settings, "bookmarks", marks)
    return f"Saved {title} under {tag}."


def bookmarks(settings: Settings, tag: str) -> str:
    marks = store.load(settings, "bookmarks", [])
    if not marks:
        return "No saved links yet."
    tag = store.clean(tag).lower()
    if not tag:
        tags: dict[str, int] = {}
        for m in marks:
            tags[m["tag"]] = tags.get(m["tag"], 0) + 1
        return f"{store.plural(len(marks), 'saved link')}. Tags: " + ", ".join(f"{t} ({n})" for t, n in tags.items()) + "."
    found = [m for m in marks if m["tag"] == tag]
    if not found:
        return f"No links tagged {tag}."
    return f"Links tagged {tag}:\n" + "\n".join(f"- {m['title']}: {m['url']}" for m in found)


def bookmark_open(settings: Settings, title: str) -> str:
    mark = store.find(store.load(settings, "bookmarks", []), "title", title)
    if mark is None:
        return "I couldn't find that saved link."
    if not _safe_url(mark["url"]):
        return "That saved link isn't a web address, so I won't open it."
    webbrowser.open(mark["url"])
    return f"Opened {mark['title']} in your browser."


def quote_save(settings: Settings, text: str, author: str, today: date) -> str:
    text = store.need(text, "quote", 500)
    quotes = store.load(settings, "quotes", [])
    if any(q["text"].lower() == text.lower() for q in quotes):
        return "You've already saved that one."
    _add_capped(quotes, {"text": text, "author": store.clean(author, 80), "saved": today.isoformat()}, "quote list")
    store.save(settings, "quotes", quotes)
    return f"Saved. You have {store.plural(len(quotes), 'quote')}."


def quote_random(settings: Settings, pick=random.choice) -> str:
    quotes = store.load(settings, "quotes", [])
    if not quotes:
        return "You haven't saved any quotes yet."
    quote = pick(quotes)
    return f"\"{quote['text']}\"" + (f" — {quote['author']}" if quote["author"] else "")


ACTIONS = ["book_add", "book_reading", "book_finished", "reading_now", "books_this_year",
           "watch_add", "watched", "watch_list", "watch_pick",
           "bookmark_save", "bookmarks", "bookmark_open", "quote_save", "quote_random"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "reading_and_watching",
        "description": "Reading list, watch list, saved links and favourite quotes. book_add (title, author), "
                       "book_reading, book_finished (optional rating 1-5), reading_now, books_this_year. watch_add "
                       "(title, kind), watched, watch_list, watch_pick picks a random one for tonight. bookmark_save "
                       "(url, title, tag), bookmarks (by tag, or all tags), bookmark_open (title). quote_save "
                       "(text, author), quote_random.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "title": {"type": "string", "description": "Book, film, series or link title."},
                "author": {"type": "string"},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                "kind": {"type": "string", "enum": ["film", "series"]},
                "url": {"type": "string", "description": "Full http(s) link."},
                "tag": {"type": "string"},
                "text": {"type": "string", "description": "The quote."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"reading_and_watching"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action, today = args.get("action"), store.today()
    title, author, kind = args.get("title") or "", args.get("author") or "", args.get("kind") or ""
    if action == "book_add":
        return book_add(settings, title, author)
    if action == "book_reading":
        return book_reading(settings, title, author)
    if action == "book_finished":
        return book_finished(settings, title, author, args.get("rating"), today)
    if action == "reading_now":
        return reading_now(settings)
    if action == "books_this_year":
        return finished_this_year(settings, today)
    if action == "watch_add":
        return watch_add(settings, title, kind)
    if action == "watched":
        return watched(settings, title, today)
    if action == "watch_list":
        return watch_list(settings, kind)
    if action == "watch_pick":
        return watch_pick(settings, kind)
    if action == "bookmark_save":
        return bookmark_save(settings, args.get("url") or "", title, args.get("tag") or "", today)
    if action == "bookmarks":
        return bookmarks(settings, args.get("tag") or "")
    if action == "bookmark_open":
        return bookmark_open(settings, title)
    if action == "quote_save":
        return quote_save(settings, args.get("text") or "", author, today)
    if action == "quote_random":
        return quote_random(settings)
    raise ValueError(f"Unknown reading action: {action}")
