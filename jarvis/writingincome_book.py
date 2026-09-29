"""Amazon KDP self-publishing helper: book tracker, chapter word counts, daily writing goal and streak, royalty calculator
(35% and 70% ebook, paperback with printing cost), blurb structure and checker, 7 keyword slots, categories, launch
checklist, honest review-request drafts and general KDP notes.

Data is in writingincome-books.json in the memory folder. Royalty sums use the delivery and printing costs you type; KDP's own
rates, price ranges and printing costs change, so every result says to check KDP's current rates. Nothing is uploaded or sent.
"""

from datetime import timedelta

import writingincome_store as wi
from config import Settings

NAMES = {"writingincome_book"}
CHECK_KDP = "Check KDP's current rates, price ranges and printing costs: they change and differ by country."
LAUNCH = [
    "Manuscript edited and proofread (ask someone else to read it too)", "Interior formatted and previewed in KDP's previewer",
    "Cover looks clear as a small thumbnail", "Title, subtitle and author name typed exactly the same everywhere",
    "Description written and checked", "Seven keyword slots filled", "Two categories chosen", "Price and royalty option chosen with the calculator",
    "Decided on an ISBN (KDP offers a free one) and on KDP Select (it needs ebook exclusivity, check the terms)",
    "Ordered a printed proof copy of the paperback and read it", "Tax information section of your KDP account completed",
    "Author page set up on Amazon", "Honest review requests drafted for readers who chose to read early",
    "Launch message ready for your own newsletter or blog", "Any affiliate links or sponsors disclosed clearly",
]
BLURB = {
    "fiction": [("Hook", ["One gripping sentence: who wants what, and what stands in the way."]),
                ("Setup", ["Two or three sentences about the main character and their world before things change."]),
                ("Conflict", ["What goes wrong. What choice do they face? Keep it specific, avoid vague words like 'journey'."]),
                ("Stakes", ["What will they lose if they fail?"]),
                ("Close", ["A last line that leaves a question, and, if it is part of a series, the series name."])],
    "nonfiction": [("Problem", ["Name the reader's problem in their own words."]), ("Promise", ["What will they be able to do after reading?"]),
                   ("What's inside", ["Three to five short bullets of what the book covers."]),
                   ("Who it's for", ["One line about the ideal reader, and who it isn't for."]),
                   ("About you", ["One line on why you are the one to write it, only true things."])],
}
RISKY = ["bestseller", "best-seller", "#1", "number one", "guaranteed", "award-winning", "amazon's choice", "free"]
REVIEW = [
    ("To readers on your mailing list", ["Hi [name], my book [title] is out. If you read it and have a minute, an honest review on Amazon "
                                          "helps other readers decide. Say whatever you really thought. Thank you for reading."]),
    ("To early readers (advance copy)", ["Thanks for reading an early copy of [title]. If you choose to, please leave an honest review "
                                          "when the book is live. There is no obligation and it doesn't need to be positive."]),
    ("At the end of the book", ["Thank you for reading [title]. If you enjoyed it, please consider leaving a short review where you "
                                 "bought it. Reviews help other readers find books they will like."]),
]
REVIEW_RULES = ("Amazon's rules: never pay for reviews, swap reviews, offer gifts or discounts for them, or only ask happy readers. "
                "Friends and family reviews can be removed. Check Amazon's current community guidelines.")


def _data(settings: Settings) -> dict:
    d = wi.load(settings, wi.BOOKS, {})
    if not isinstance(d.get("books"), list):
        d["books"] = []
    return d


def _book(d: dict, ref) -> dict:
    if not wi.clean(ref) and len(d["books"]) == 1:
        return d["books"][0]
    return wi.pick(d["books"], ref, "title", "book")


def _words(book: dict) -> int:
    return sum(c["words"] for c in book["chapters"]) if book["chapters"] else sum(e["words"] for e in book["log"])


def _days(n: int) -> str:
    return f"{n} day{'s' * (n != 1)}"


def _streak(book: dict) -> int:
    goal = book.get("daily_goal", 0) or 1
    by_day = {}
    for e in book["log"]:
        by_day[e["date"]] = by_day.get(e["date"], 0) + e["words"]
    day = wi.today()
    if by_day.get(day.isoformat(), 0) < goal:
        day -= timedelta(days=1)
    n = 0
    while by_day.get(day.isoformat(), 0) >= goal:
        n, day = n + 1, day - timedelta(days=1)
    return n


def _recent(book: dict, days: int = 14) -> list[tuple]:
    by_day = {}
    for e in book["log"]:
        by_day[e["date"]] = by_day.get(e["date"], 0) + e["words"]
    today = wi.today()
    return [(today - timedelta(days=i), by_day.get((today - timedelta(days=i)).isoformat(), 0)) for i in range(days - 1, -1, -1)]


def add_book(settings: Settings, args: dict):
    d = _data(settings)
    if len(d["books"]) >= 100:
        raise ValueError("That's plenty of books; remove one first.")
    deadline = wi.parse_date(args.get("date"), "deadline")
    row = {"id": wi.next_id(d["books"]), "title": wi.need(args.get("title"), "book title", 100),
           "target_words": wi.whole(args, "target_words", "word target", default=0), "daily_goal": wi.whole(args, "daily_goal", "daily goal", zero=True, default=0),
           "deadline": deadline.isoformat() if deadline else "",
           "chapters": [], "log": [], "blurb": "", "keywords": [""] * 7, "categories": [], "launch": []}
    d["books"].append(row)
    wi.save(settings, wi.BOOKS, d)
    return f"Started the book project {row['title']}" + (f", target {row['target_words']:,} words." if row["target_words"] else ".")


def list_books(settings: Settings, args: dict):
    d = _data(settings)
    if not d["books"]:
        raise ValueError("No book projects yet. Say the title and word target to start one.")
    rows = []
    for b in d["books"]:
        w, t = _words(b), b["target_words"]
        rows.append([str(b["id"]), b["title"], f"{w:,}", f"{t:,} ({round(100 * w / t)}%)" if t else "no target", str(_streak(b)) + " days"])
    return wi.table(f"{len(rows)} book projects.", "Book projects", ["#", "Book", "Words", "Target", "Streak"], rows, "writingincome-books")


def remove_book(settings: Settings, args: dict):
    d = _data(settings)
    b = _book(d, args.get("book"))
    ask = wi.confirm_first(args, f"the book project {b['title']} with all its notes and word counts")
    if ask:
        return ask
    d["books"] = [x for x in d["books"] if x is not b]
    wi.save(settings, wi.BOOKS, d)
    return f"Removed {b['title']}."


def log_chapter(settings: Settings, args: dict):
    d = _data(settings)
    b = _book(d, args.get("book"))
    ref = wi.clean(args.get("chapter"), 60)
    if not ref:
        raise ValueError("Which chapter? Give its number or name.")
    words = wi.whole(args, "words", "chapter word count", zero=True)
    ch = next((c for c in b["chapters"] if str(c["n"]) == ref.lstrip("#") or c["name"].lower() == ref.lower()), None)
    if ch is None:
        ch = {"n": max([c["n"] for c in b["chapters"]] + [0]) + 1, "name": ref if not ref.isdigit() else f"Chapter {ref}", "words": 0, "target": 0}
        b["chapters"].append(ch)
    ch["words"] = words
    if args.get("target_words") is not None:
        ch["target"] = wi.whole(args, "target_words", "chapter target", zero=True)
    wi.save(settings, wi.BOOKS, d)
    return f"{ch['name']} is at {words:,} words. {b['title']} is now {_words(b):,} words."


def log_words(settings: Settings, args: dict):
    d = _data(settings)
    b = _book(d, args.get("book"))
    words = wi.whole(args, "words", "words written today")
    b["log"].append({"date": wi.day_arg(args).isoformat(), "words": words})
    wi.save(settings, wi.BOOKS, d)
    today = sum(e["words"] for e in b["log"] if e["date"] == wi.today().isoformat())
    goal = b["daily_goal"]
    hit = f" That's {today:,} of {goal:,} today." if goal else ""
    return f"Logged {words:,} words on {b['title']}.{hit} Streak: {_days(_streak(b))}."


def set_daily_goal(settings: Settings, args: dict):
    d = _data(settings)
    b = _book(d, args.get("book"))
    b["daily_goal"] = wi.whole(args, "daily_goal", "daily word goal", zero=True)
    wi.save(settings, wi.BOOKS, d)
    return f"Daily goal for {b['title']} is {b['daily_goal']:,} words."


def book_progress(settings: Settings, args: dict):
    d = _data(settings)
    b = _book(d, args.get("book"))
    w, t = _words(b), b["target_words"]
    rows = [("Book", f"{w:,}" + (f" of {t:,}" if t else ""), 100 * w / t if t else 0, "words written")]
    top = max([c["words"] for c in b["chapters"]] + [1])
    rows += [(c["name"], f"{c['words']:,}", 100 * c["words"] / (c["target"] or top), f"of {c['target']:,}" if c["target"] else "")
             for c in b["chapters"][:20]]
    today = wi.today()
    notes = [f"Streak: {_days(_streak(b))}" + (f" at {b['daily_goal']:,} words a day." if b["daily_goal"] else " (any words count).")]
    left = max(t - w, 0) if t else 0
    recent = sum(n for _, n in _recent(b)) / 14
    if left and recent:
        notes.append(f"At your last 14 days' average of {round(recent)} words a day you'd finish in about {int(-(-left // recent))} days. A rough guess.")
    if b["deadline"] and left:
        day = wi.parse_date(b["deadline"])
        gap = (day - today).days
        notes.append(f"Deadline {wi.short(day)} ({wi.until(day, today)})" + (f": about {-(-left // gap):,} words a day needed." if gap > 0 else "."))
    return wi.meter(f"{b['title']}: {w:,} words" + (f", {round(100 * w / t)}% of target." if t else "."), b["title"], rows, " ".join(notes))


def writing_chart(settings: Settings, args: dict):
    b = _book(_data(settings), args.get("book"))
    days = _recent(b)
    total = sum(n for _, n in days)
    return wi.chart(f"{total:,} words in the last 14 days on {b['title']}.", f"Daily words: {b['title']}", [wi.short(d) for d, _ in days],
                    [n for _, n in days], "bar", "words", "writingincome-daily")


def _royalty(fmt: str, price: float, plan: int, delivery: float, printing: float, print_pct: float) -> float:
    if fmt == "ebook":
        return round(price * plan / 100 - (delivery if plan == 70 else 0), 2)
    return round(price * print_pct / 100 - printing, 2)


def royalty_calc(settings: Settings, args: dict):
    fmt = wi.clean(args.get("format")).lower() or "ebook"
    fmt = "paperback" if fmt in ("print", "book") else fmt
    if fmt not in ("ebook", "paperback", "hardcover"):
        raise ValueError("Format should be ebook, paperback or hardcover.")
    price = wi.arg(args, "price", "list price")
    sales = wi.whole(args, "copies", "copies sold", zero=True, default=0)
    rows, notes = [("List price", wi.pounds(price))], [CHECK_KDP, wi.HONEST]
    if fmt == "ebook":
        delivery = wi.arg(args, "delivery_cost", "ebook delivery cost per copy", zero=True, default=0.0)
        r35, r70 = _royalty(fmt, price, 35, 0, 0, 0), _royalty(fmt, price, 70, delivery, 0, 0)
        rows += [("35% royalty option", wi.pounds(r35)), (f"70% royalty option (less {wi.pounds(delivery)} delivery)", wi.pounds(r70))]
        best = max(r35, r70)
        notes.insert(0, "The 70% option only applies within a price range and in certain countries, and the delivery cost depends on your file size.")
        head = wi.pounds(best)
        sub = "per copy on the better option, before tax"
    else:
        printing = wi.arg(args, "print_cost", "printing cost per copy", zero=True)
        pct = wi.arg(args, "royalty_pct", "print royalty percentage", default=60.0, top=100)
        best = _royalty(fmt, price, 0, 0, printing, pct)
        rows += [(f"{pct:g}% of price", wi.pounds(round(price * pct / 100, 2))), ("Printing cost you typed", wi.pounds(printing))]
        head, sub = wi.pounds(best), "per copy, before tax"
        if best <= 0:
            notes.insert(0, "That price doesn't cover printing at this royalty rate. Try a higher price or fewer pages.")
    if sales:
        rows.append((f"{sales:,} copies", wi.pounds(round(best * sales, 2))))
    return wi.result(f"About {head} a copy for {fmt}. {CHECK_KDP}", "KDP royalty", head, sub, rows, notes)


def royalty_ladder(settings: Settings, args: dict):
    prices = [wi.number(p, "price") for p in str(args.get("prices") or "2.99, 3.99, 4.99, 6.99, 9.99").split(",") if p.strip()][:12]
    delivery = wi.arg(args, "delivery_cost", "ebook delivery cost per copy", zero=True, default=0.0)
    rows = [[wi.pounds(p), wi.pounds(_royalty("ebook", p, 35, 0, 0, 0)), wi.pounds(_royalty("ebook", p, 70, delivery, 0, 0))] for p in prices]
    return wi.table(f"Ebook royalty per copy at {len(rows)} prices. {CHECK_KDP}", "Ebook price ladder", ["Price", "35% option", "70% option"],
                    rows, "writingincome-ladder")


def copies_for_target(settings: Settings, args: dict):
    goal = wi.arg(args, "target", "amount you want to earn")
    per = _royalty_from_args(args)
    if per <= 0:
        raise ValueError("Each copy earns nothing at those numbers, so no number of copies gets there.")
    copies = -(-goal // per)
    return wi.result(f"About {int(copies):,} copies to earn {wi.pounds(goal)}. {wi.HONEST}", "Copies needed", f"{int(copies):,}", "copies, a what-if only",
                     [("Per copy", wi.pounds(per)), ("Goal", wi.pounds(goal))], [CHECK_KDP, wi.HONEST])


def _royalty_from_args(args: dict) -> float:
    fmt = wi.clean(args.get("format")).lower() or "ebook"
    price = wi.arg(args, "price", "list price")
    if fmt == "ebook":
        return _royalty("ebook", price, int(wi.arg(args, "plan", "royalty option 35 or 70", default=70)), wi.arg(args, "delivery_cost", "delivery cost", True, 0.0), 0, 0)
    return _royalty("paperback", price, 0, 0, wi.arg(args, "print_cost", "printing cost", True), wi.arg(args, "royalty_pct", "royalty percentage", default=60.0))


def pages_estimate(settings: Settings, args: dict):
    words = wi.whole(args, "words", "word count")
    per = wi.whole(args, "words_per_page", "words per page", default=275, top=1000)
    pages = -(-words // per)
    mins = round(words / 238)
    return wi.result(f"About {pages} pages and {mins // 60}h {mins % 60}m reading time.", "Pages estimate", f"{pages} pages", f"at {per} words a page",
                     [("Words", f"{words:,}"), ("Reading time", f"{mins // 60}h {mins % 60}m at 238 words a minute")],
                     ["Real page count depends on trim size, font and spacing. KDP's previewer shows the true count, and printing cost depends on it."])


def blurb_template(settings: Settings, args: dict):
    kind = "nonfiction" if wi.clean(args.get("kind")).lower().startswith("non") else "fiction"
    return wi.guide(f"A {kind} blurb structure. I can draft one from your notes.", f"Blurb: {kind}", BLURB[kind],
                    "Keep it about 150 to 250 words, with short paragraphs and no claims you can't prove.")


def check_blurb(settings: Settings, args: dict):
    text = str(args.get("text") or "").strip()
    if len(wi.words_of(text)) < 10:
        raise ValueError("Paste the blurb text to check.")
    words, lower = len(wi.words_of(text)), text.lower()
    found = [w for w in RISKY if w in lower]
    first = wi.sentences_of(text)[0]
    items = [("Length", "ok" if 100 <= words <= 300 else "warn", f"{words} words. About 150 to 250 reads well; KDP's limit is around 4,000 characters."),
             ("Character limit", "ok" if len(text) <= 4000 else "fail", f"{len(text)} characters of about 4,000."),
             ("Opening line", "ok" if len(wi.words_of(first)) <= 25 else "warn", f"{len(wi.words_of(first))} words. Make it short and gripping."),
             ("Claims", "warn" if found else "ok", ("Check these are true and allowed: " + ", ".join(found)) if found else "No big claims found."),
             ("Paragraphs", "ok" if "\n" in text else "warn", "Broken into paragraphs." if "\n" in text else "One block of text; break it up.")]
    saved = ""
    if args.get("book"):
        d = _data(settings)
        b = _book(d, args["book"])
        b["blurb"] = text[:4000]
        wi.save(settings, wi.BOOKS, d)
        saved = f" Saved as the blurb for {b['title']}."
    bad = sum(1 for i in items if i[1] != "ok")
    head = "Looks good" if not bad else f"{bad} to look at"
    return wi.check(f"{head}.{saved}", "Blurb check", head, items, "Amazon's description rules change: check what KDP currently allows.")


def keywords_set(settings: Settings, args: dict):
    d = _data(settings)
    b = _book(d, args.get("book"))
    slot = wi.whole(args, "slot", "slot number", top=7)
    phrase = wi.need(args.get("keyword"), "keyword phrase", 50)
    b["keywords"][slot - 1] = phrase
    wi.save(settings, wi.BOOKS, d)
    return f"Slot {slot} for {b['title']} is now '{phrase}'. {sum(1 for k in b['keywords'] if k)} of 7 filled."


def categories_set(settings: Settings, args: dict):
    d = _data(settings)
    b = _book(d, args.get("book"))
    cats = [wi.clean(c, 100) for c in str(args.get("categories") or "").split(",") if wi.clean(c)][:5]
    if not cats:
        raise ValueError("Give the categories you're considering, separated by commas.")
    b["categories"] = cats
    wi.save(settings, wi.BOOKS, d)
    return f"Noted {len(cats)} categories for {b['title']}. Check the exact category names in KDP."


def keywords_show(settings: Settings, args: dict):
    b = _book(_data(settings), args.get("book"))
    slots = [f"{i + 1}. {k or '(empty)'}" for i, k in enumerate(b["keywords"])]
    return wi.guide(f"{sum(1 for k in b['keywords'] if k)} of 7 keyword slots filled for {b['title']}.", f"Keywords: {b['title']}",
                    [("Seven keyword slots", slots), ("Category notes", b["categories"] or ["None yet."]),
                     ("Tips", ["Use phrases a reader would type, not single words.", "Don't repeat words from your title; they already count.",
                               "Don't use other authors' names, trademarks or claims like 'bestseller'."])],
                    "KDP's slot count and limits can change. Check them when you publish.")


def launch_checklist(settings: Settings, args: dict):
    b = _book(_data(settings), args.get("book"))
    done = set(b["launch"])
    items = [(f"{i + 1}. {s}", "ok" if i in done else "todo", "") for i, s in enumerate(LAUNCH)]
    head = f"{len(done)} of {len(LAUNCH)} done"
    nxt = min([i for i in range(len(LAUNCH)) if i not in done] or [0]) + 1
    return wi.check(f"Launch checklist for {b['title']}: {head}.", f"Launch: {b['title']}", head, items, CHECK_KDP,
                    [{"label": "Tick next", "say": f"Tick launch step {nxt} for {b['title']}"}])


def launch_tick(settings: Settings, args: dict):
    d = _data(settings)
    b = _book(d, args.get("book"))
    step = wi.whole(args, "step", "step number", top=len(LAUNCH)) - 1
    said = "Unticked" if step in b["launch"] else "Ticked"
    b["launch"] = [s for s in b["launch"] if s != step] if step in b["launch"] else b["launch"] + [step]
    wi.save(settings, wi.BOOKS, d)
    return f"{said} launch step {step + 1}. {len(b['launch'])} of {len(LAUNCH)} done."


def review_requests(settings: Settings, args: dict):
    return wi.guide("Three honest review-request drafts. Copy and send them yourself.", "Review requests", REVIEW, REVIEW_RULES)


def kdp_notes(settings: Settings, args: dict):
    return wi.guide("General notes on publishing with KDP.", "KDP notes", [
        ("Formats", ["Ebook, paperback and hardcover are set up separately and each has its own price.",
                     "Paperback and hardcover are printed on demand; the printing cost depends on pages, trim size and ink."]),
        ("Royalties", ["Ebooks offer a 35% or 70% option; the 70% option has price limits and a delivery cost. Print royalty is a percentage "
                       "of the price minus printing. Use the royalty calculator with your own numbers."]),
        ("Rights and ISBN", ["KDP can give a free ISBN, or you can buy your own. KDP Select needs ebook exclusivity for a period; read the terms."]),
        ("Money and tax", ["KDP pays a while after the month of the sale. You complete a tax information section in your account.",
                           "Royalties are income and may need declaring. " + wi.TAX]),
        ("Honest expectations", ["Most books sell slowly at first. Nothing here forecasts sales."])], CHECK_KDP)


ACTIONS = {"add_book": add_book, "list_books": list_books, "remove_book": remove_book, "log_chapter": log_chapter, "log_words": log_words,
           "set_daily_goal": set_daily_goal, "book_progress": book_progress, "writing_chart": writing_chart, "royalty_calc": royalty_calc,
           "royalty_ladder": royalty_ladder, "copies_for_target": copies_for_target, "pages_estimate": pages_estimate,
           "blurb_template": blurb_template, "check_blurb": check_blurb, "keywords_set": keywords_set, "categories_set": categories_set,
           "keywords_show": keywords_show, "launch_checklist": launch_checklist, "launch_tick": launch_tick,
           "review_requests": review_requests, "kdp_notes": kdp_notes}


def tool_definitions() -> list[dict]:
    return [{
        "name": "writingincome_book",
        "description": "Amazon KDP self-publishing helper: book project tracker, chapter word counts, daily writing goal and streak, progress and "
                       "chart, KDP royalty calculator (ebook 35%/70% with delivery cost, paperback/hardcover with printing cost, price ladder, "
                       "copies needed), pages estimate, blurb structure and checker, 7 keyword slots, categories, launch checklist, honest "
                       "review-request drafts, KDP notes. Costs are typed by the user; note to check KDP's current rates. Set confirmed only "
                       "after the user agrees to remove_book.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "book": {"type": "string", "description": "Book number or title (optional if only one)."}, "title": {"type": "string"},
                "target_words": {"type": "number"}, "daily_goal": {"type": "number"}, "words": {"type": "number"},
                "chapter": {"type": "string", "description": "Chapter number or name."}, "date": {"type": "string", "description": "YYYY-MM-DD."},
                "format": {"type": "string", "enum": ["ebook", "paperback", "hardcover"]}, "price": {"type": "number"},
                "prices": {"type": "string", "description": "Comma-separated prices for the ladder."},
                "delivery_cost": {"type": "number", "description": "Ebook delivery cost per copy, from KDP."},
                "print_cost": {"type": "number", "description": "Printing cost per copy, from KDP."},
                "royalty_pct": {"type": "number"}, "plan": {"type": "number", "enum": [35, 70]}, "copies": {"type": "number"},
                "target": {"type": "number", "description": "Amount to earn."}, "words_per_page": {"type": "number"},
                "kind": {"type": "string", "description": "fiction or nonfiction."}, "text": {"type": "string"},
                "slot": {"type": "number", "description": "Keyword slot 1 to 7."}, "keyword": {"type": "string"},
                "categories": {"type": "string", "description": "Comma-separated."}, "step": {"type": "number"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    return wi.dispatch(ACTIONS, settings, args)
