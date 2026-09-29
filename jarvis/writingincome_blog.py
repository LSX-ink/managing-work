"""Blog planner: a post pipeline (idea, draft, published), a plain-words SEO checklist per post, title and meta description
length checker, keyword and heading checks on text you paste, internal link planner, Flesch reading ease, word targets,
URL slugs and reminders to refresh old posts.

Data is in writingincome-blog.json in the memory folder. Measuring happens on this PC; no search engine or site is contacted,
and nobody can promise a post will rank. Results pop up as tables, a board and writingincome-* cards.
"""

import re
from datetime import timedelta

import writingincome_store as wi
from config import Settings

NAMES = {"writingincome_blog"}
STATUSES = ["idea", "draft", "published"]
ALIAS = {"drafting": "draft", "drafted": "draft", "live": "published", "done": "published", "ideas": "idea"}
SEO = [
    "One clear question: you can say in a sentence what the post answers",
    "The phrase people would search for is in the title",
    "The phrase is in the first paragraph",
    "The phrase, or a close variation, is in at least one heading",
    "Title is short enough not to be cut off (about 60 characters)",
    "Meta description written (about 120 to 155 characters)",
    "Web address (URL) is short and readable",
    "Headings are in order: one main title, then sections",
    "Every image has a short description (alt text)",
    "Two or three links to your other posts",
    "At least one link to a useful outside source",
    "Read it on a phone: short paragraphs, nothing cramped",
    "Proofread out loud once",
    "States when it was written or last updated",
]
TARGETS = [
    ("News or quick update", "300 to 600 words"), ("Opinion or personal story", "600 to 1,200 words"),
    ("List post", "1,000 to 1,800 words"), ("How-to guide", "1,200 to 2,000 words"), ("Review or comparison", "1,200 to 2,000 words"),
    ("Pillar or complete guide", "2,000 to 3,500 words"),
]


def _data(settings: Settings) -> dict:
    d = wi.load(settings, wi.BLOG, {})
    for key in ("posts", "links"):
        if not isinstance(d.get(key), list):
            d[key] = []
    return d


def _status(value, default: str = "idea") -> str:
    text = wi.clean(value).lower() or default
    text = ALIAS.get(text, text)
    if text not in STATUSES:
        raise ValueError("Status should be idea, draft or published.")
    return text


def _post(d: dict, ref) -> dict:
    return wi.pick(d["posts"], ref, "title", "post")


def _touched(post: dict):
    return wi.parse_date(post.get("updated") or post.get("published")) or wi.today()


def add_post(settings: Settings, args: dict):
    d = _data(settings)
    if len(d["posts"]) >= wi.MAX_ROWS:
        raise ValueError("The post list is full; remove old posts first.")
    status = _status(args.get("status"))
    row = {"id": wi.next_id(d["posts"]), "title": wi.need(args.get("title"), "post title", 120), "status": status,
           "keyword": wi.clean(args.get("keyword"), 60), "target_words": wi.whole(args, "target_words", "word target", default=0),
           "url": wi.clean(args.get("url"), 200), "published": "", "updated": "", "seo": [], "notes": wi.clean(args.get("notes"), 300)}
    if status == "published":
        row["published"] = wi.day_arg(args).isoformat()
    elif args.get("date"):
        row["due"] = wi.parse_date(args["date"], "date").isoformat()
    d["posts"].append(row)
    wi.save(settings, wi.BLOG, d)
    return f"Added post {row['id']}, {row['title']}, as {status}."


def update_post(settings: Settings, args: dict):
    d = _data(settings)
    row = _post(d, args.get("post"))
    if args.get("status"):
        row["status"] = _status(args["status"])
        if row["status"] == "published" and not row["published"]:
            row["published"] = wi.day_arg(args).isoformat()
    if args.get("date") and row["status"] != "published":
        row["due"] = wi.parse_date(args["date"], "date").isoformat()
    for key, limit in (("title", 120), ("keyword", 60), ("url", 200), ("notes", 300)):
        if args.get(key) is not None:
            row[key] = wi.clean(args[key], limit)
    if args.get("target_words") is not None:
        row["target_words"] = wi.whole(args, "target_words", "word target", zero=True)
    wi.save(settings, wi.BLOG, d)
    return f"Updated post {row['id']}, {row['title']}: {row['status']}."


def remove_post(settings: Settings, args: dict):
    d = _data(settings)
    row = _post(d, args.get("post"))
    ask = wi.confirm_first(args, f"the post {row['title']} and its links from the planner")
    if ask:
        return ask
    d["posts"] = [p for p in d["posts"] if p is not row]
    d["links"] = [k for k in d["links"] if row["id"] not in (k["from"], k["to"])]
    wi.save(settings, wi.BLOG, d)
    return f"Removed {row['title']}."


def pipeline(settings: Settings, args: dict):
    d = _data(settings)
    if not d["posts"]:
        raise ValueError("No posts yet. Say a title to add an idea.")
    cols = []
    for status in STATUSES:
        cards = [(p["title"], " · ".join(x for x in (p["keyword"], f"{p['target_words']} words" if p["target_words"] else "",
                                                      p.get("due", "")) if x), f"Show the SEO checklist for {p['title']}")
                 for p in d["posts"] if p["status"] == status]
        cols.append((f"{status.title()} ({len(cards)})", cards))
    return wi.board(f"{len(d['posts'])} post{'s' * (len(d['posts']) != 1)} in your pipeline.", "Blog pipeline", cols, "Tap a post to see its SEO checklist.")


def seo_checklist(settings: Settings, args: dict):
    d = _data(settings)
    post = _post(d, args.get("post"))
    done = set(post["seo"])
    items = [(f"{i + 1}. {label}", "ok" if i in done else "todo", "") for i, label in enumerate(SEO)]
    head = f"{len(done)} of {len(SEO)} done"
    buttons = [{"label": "Tick next", "say": f"Tick SEO step {min([i for i in range(len(SEO)) if i not in done] or [0]) + 1} for {post['title']}"}]
    return wi.check(f"SEO checklist for {post['title']}: {head}.", f"SEO: {post['title']}", head, items,
                    "Good habits, not a ranking promise. Nobody can guarantee where a post will appear.", buttons)


def seo_tick(settings: Settings, args: dict):
    d = _data(settings)
    post = _post(d, args.get("post"))
    step = wi.whole(args, "step", "step number", top=len(SEO)) - 1
    if step in post["seo"]:
        post["seo"].remove(step)
        said = "Unticked"
    else:
        post["seo"].append(step)
        said = "Ticked"
    wi.save(settings, wi.BLOG, d)
    return f"{said} step {step + 1} for {post['title']}: {SEO[step]}. {len(post['seo'])} of {len(SEO)} done."


def check_meta(settings: Settings, args: dict):
    title, meta = wi.need(args.get("title"), "title", 200), wi.clean(args.get("meta"), 500)
    key = wi.clean(args.get("keyword"), 60).lower()
    items = [("Title length", "ok" if 30 <= len(title) <= 60 else "warn",
              f"{len(title)} characters. About 30 to 60 usually shows in full; long titles get cut off.")]
    if meta:
        items.append(("Meta description length", "ok" if 70 <= len(meta) <= 160 else "warn",
                      f"{len(meta)} characters. About 120 to 155 is the usual target."))
    else:
        items.append(("Meta description", "warn", "None given. Write one that says what the reader gets."))
    if key:
        items.append(("Phrase in title", "ok" if key in title.lower() else "warn", f"'{key}' " + ("is" if key in title.lower() else "is not") + " in the title."))
        if meta:
            items.append(("Phrase in meta description", "ok" if key in meta.lower() else "warn",
                          f"'{key}' " + ("is" if key in meta.lower() else "is not") + " in the description."))
    if meta and title.lower() == meta.lower():
        items.append(("Different from title", "warn", "The description just repeats the title."))
    items.append(("Suggested web address", "ok", "/" + wi.slugify(key or title)))
    warn = sum(1 for i in items if i[1] == "warn")
    head = "Looks fine" if not warn else f"{warn} to look at"
    return wi.check(f"{head}: title {len(title)} characters" + (f", description {len(meta)}." if meta else "."), "Title and meta check", head, items,
                    "Search engines may rewrite what they show, and real limits depend on pixel width, so these counts are a guide.")


def _headings(text: str) -> list[tuple[int, str]]:
    return [(len(m.group(1)), m.group(2).strip()) for m in re.finditer(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", str(text or ""), flags=re.M)]


def keyword_check(settings: Settings, args: dict):
    text, key = str(args.get("text") or ""), wi.need(args.get("keyword"), "keyword phrase", 60).lower()
    if len(wi.words_of(text)) < 20:
        raise ValueError("Paste the post text (with # headings if you can) and the keyword phrase.")
    title = wi.clean(args.get("title"), 200)
    heads = _headings(text)
    body = wi.plain(text).lower()
    words = wi.words_of(body)
    first = " ".join(words[:100]).lower()
    count = len(re.findall(re.escape(key), body))
    density = round(100 * count * len(key.split()) / max(len(words), 1), 1)
    in_heads = [h for _, h in heads if key in h.lower()]
    items = [("Title", "ok" if key in title.lower() else ("warn" if title else "todo"),
              ("Has the phrase." if key in title.lower() else "Missing from the title.") if title else "No title given to check."),
             ("First 100 words", "ok" if key in first else "warn", "Phrase appears early." if key in first else "Phrase is not in the first 100 words."),
             ("Headings", "ok" if in_heads else "warn", f"{len(in_heads)} of {len(heads)} headings include it." if heads else "No # headings found."),
             ("How often", "ok" if 0.3 <= density <= 2.5 else "warn",
              f"{count} times in {len(words)} words ({density}%). Natural writing usually lands well under 2.5%.")]
    warn = sum(1 for i in items if i[1] == "warn")
    head = "Good use of the phrase" if not warn else f"{warn} to look at"
    return wi.check(f"'{key}' appears {count} times; {head.lower()}.", f"Keyword check: {key}", head, items,
                    "Write for people first. Stuffing the phrase in hurts readability and won't help.")


def heading_structure(settings: Settings, args: dict):
    heads = _headings(args.get("text"))
    if not heads:
        raise ValueError("I found no # headings. Paste the text with # for the title and ## for sections.")
    h1 = sum(1 for lvl, _ in heads if lvl == 1)
    skipped = [h for prev, h in zip(heads, heads[1:]) if h[0] > prev[0] + 1]
    items = [("One main title", "ok" if h1 == 1 else "warn", f"{h1} top-level (#) headings; aim for exactly one."),
             ("No skipped levels", "ok" if not skipped else "warn", "Levels step down one at a time." if not skipped else
              "Jumps to: " + ", ".join(h[1][:30] for h in skipped[:3])),
             ("Enough sections", "ok" if len(heads) >= 3 else "warn", f"{len(heads)} headings. Breaking text up helps readers.")]
    outline = [("Outline", ["  " * (lvl - 1) + f"H{lvl} {h}" for lvl, h in heads[:30]])]
    warn = sum(1 for i in items if i[1] == "warn")
    return wi.check(f"{len(heads)} headings, {warn} to look at.", "Heading structure", "Tidy" if not warn else f"{warn} to look at",
                    items + [(o, "ok", "") for o in outline[0][1]], "Headings help readers and screen readers skim the post.")


def _grade(grade: float) -> str:
    return "a young reader could follow it" if grade < 1 else f"about grade {grade}"


def readability(settings: Settings, args: dict):
    r = wi.reading_ease(args.get("text"))
    rows = [("Words", str(r["words"])), ("Sentences", str(r["sentences"])), ("Average sentence", f"{r['avg_sentence']} words"),
            ("School grade level", str(r["grade"])), ("Sentences over 25 words", str(len(r["long"])))]
    target = wi.whole(args, "target_words", "word target", zero=True, default=0)
    if target:
        rows.append(("Against target", f"{r['words']} of {target} ({round(100 * r['words'] / target)}%)"))
    notes = ["Flesch reading ease: 60 to 70 is plain English, 70 and up is easy. A score is a guide, not a verdict.",
             "Try: shorter sentences, everyday words, one idea per paragraph."]
    if r["long"]:
        notes.insert(0, "A long one: " + r["long"][0][:120] + "...")
    return wi.result(f"Reading ease {r['ease']}, {r['band']}, {_grade(r['grade'])}.", "Readability", str(r["ease"]), r["band"], rows, notes)


def word_targets(settings: Settings, args: dict):
    sections = [("Rough lengths by post type", [f"{name}: {size}" for name, size in TARGETS])]
    text = "Rough word counts by post type."
    if args.get("post") or args.get("words"):
        d = _data(settings)
        row = _post(d, args.get("post")) if args.get("post") else None
        have = wi.whole(args, "words", "word count so far", zero=True)
        goal = (row or {}).get("target_words") or wi.whole(args, "target_words", "word target")
        if row:
            row["words"] = have
            wi.save(settings, wi.BLOG, d)
        pct = round(100 * have / goal)
        text = f"{have} of {goal} words, {pct}%."
        sections.insert(0, ("Your post", [f"{have} of {goal} words ({pct}%)", f"{max(goal - have, 0)} to go"]))
    return wi.guide(text, "Word targets", sections, "Longer isn't better. Match the length to what the reader needs, and cut padding.")


def add_link(settings: Settings, args: dict):
    d = _data(settings)
    src, dst = _post(d, args.get("post")), _post(d, args.get("to_post"))
    if src is dst:
        raise ValueError("Pick two different posts for an internal link.")
    if any(k["from"] == src["id"] and k["to"] == dst["id"] for k in d["links"]):
        raise ValueError("That link is already planned.")
    d["links"].append({"id": wi.next_id(d["links"]), "from": src["id"], "to": dst["id"], "anchor": wi.clean(args.get("anchor"), 80) or dst["keyword"] or dst["title"]})
    wi.save(settings, wi.BLOG, d)
    return f"Planned a link from {src['title']} to {dst['title']}."


def link_plan(settings: Settings, args: dict):
    d = _data(settings)
    names = {p["id"]: p["title"] for p in d["posts"]}
    rows = [[names.get(k["from"], "?"), names.get(k["to"], "?"), k["anchor"]] for k in d["links"]]
    live = [p for p in d["posts"] if p["status"] != "idea"]
    linked_to = {k["to"] for k in d["links"]}
    orphans = [p["title"] for p in live if p["id"] not in linked_to]
    if not d["posts"]:
        raise ValueError("No posts yet, so nothing to link.")
    text = f"{len(rows)} planned links." + (f" {len(orphans)} posts have no link pointing to them." if orphans else "")
    return wi.guide(text, "Internal links", [("Planned links", [f"{a} -> {b} (anchor: {c})" for a, b, c in rows] or ["None yet."]),
                                              ("Posts nothing links to", orphans or ["None. Every post has a link in."])],
                    "Link from older popular posts to newer ones, using words that describe the page you link to.")


def refresh_due(settings: Settings, args: dict):
    d = _data(settings)
    days = wi.whole(args, "days", "number of days", default=180, top=3650)
    cutoff = wi.today() - timedelta(days=days)
    old = sorted([p for p in d["posts"] if p["status"] == "published" and _touched(p) <= cutoff], key=_touched)
    if not old:
        return f"No published post is older than {days} days without an update."
    rows = [[str(p["id"]), p["title"], wi.short(_touched(p)), f"{(wi.today() - _touched(p)).days} days"] for p in old]
    return wi.table(f"{len(old)} posts could do with a refresh.", "Posts to refresh", ["#", "Post", "Last touched", "Age"], rows,
                    "writingincome-refresh")


def mark_refreshed(settings: Settings, args: dict):
    d = _data(settings)
    row = _post(d, args.get("post"))
    row["updated"] = wi.day_arg(args).isoformat()
    wi.save(settings, wi.BLOG, d)
    return f"Marked {row['title']} as refreshed on {wi.short(wi.parse_date(row['updated']))}."


def make_slug(settings: Settings, args: dict):
    slug = wi.slugify(wi.need(args.get("title"), "title", 200))
    return wi.result(f"Suggested web address: {slug}.", "URL slug", "/" + slug, f"{len(slug)} characters",
                     notes=["Keep it short, lowercase, with hyphens. Once a post is live, changing its address needs a redirect."])


ACTIONS = {"add_post": add_post, "update_post": update_post, "pipeline": pipeline, "remove_post": remove_post,
           "seo_checklist": seo_checklist, "seo_tick": seo_tick, "check_meta": check_meta, "keyword_check": keyword_check,
           "heading_structure": heading_structure, "readability": readability, "word_targets": word_targets, "add_link": add_link,
           "link_plan": link_plan, "refresh_due": refresh_due, "mark_refreshed": mark_refreshed, "make_slug": make_slug}


def tool_definitions() -> list[dict]:
    return [{
        "name": "writingincome_blog",
        "description": "Blog planner for writers: post pipeline idea/draft/published, per-post SEO checklist in plain words, title and meta "
                       "description length checker, keyword-in-title/heading checker and heading structure on pasted text, Flesch "
                       "readability, word targets, URL slug, internal link planner, reminders to refresh old posts. Measures locally; "
                       "never promises ranking. Set confirmed only after the user agrees to remove_post.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "post": {"type": "string", "description": "Post number or title."}, "to_post": {"type": "string"},
                "title": {"type": "string"}, "meta": {"type": "string", "description": "Meta description to check."},
                "keyword": {"type": "string", "description": "Target phrase."}, "status": {"type": "string", "enum": STATUSES},
                "text": {"type": "string", "description": "Pasted post text, Markdown headings with #."},
                "target_words": {"type": "number"}, "words": {"type": "number", "description": "Words written so far."},
                "date": {"type": "string", "description": "YYYY-MM-DD."}, "url": {"type": "string"}, "notes": {"type": "string"},
                "anchor": {"type": "string"}, "step": {"type": "number", "description": "SEO checklist step number."},
                "days": {"type": "number", "description": "refresh_due: age in days (default 180)."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    return wi.dispatch(ACTIONS, settings, args)
