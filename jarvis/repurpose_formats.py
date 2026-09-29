"""Repurpose part 2: turn one script into other formats. Splitting into a series with cliffhangers, X thread packing,
quote picking, title and thumbnail-text options and checks, platform limits and calls to action are worked out here; the
rewrites into Shorts, Reels, pins, blog posts, newsletters and podcast points come back as a short brief that Claude
writes from.

Nothing is posted or sent anywhere, and no video, picture or voice is made.
"""

import re

import homestore as hs
import repurpose_store as store
import screen
from config import Settings

ACTIONS = ["series_split", "series_show", "shorts_version", "reels_version", "pin_version", "thread_version",
           "blog_version", "newsletter_version", "podcast_points", "titles", "title_check", "thumbnail_text",
           "thumb_check", "quote_cards", "char_limits", "limits_check", "cta_swap", "format_guide"]
# key: (what it is, target words, how to write it)
VERSIONS = {
    "shorts_version": ("YouTube Short", 110, "Vertical, under 60 seconds. Open with the hook in the first sentence, one idea "
                       "per line, no intro, end on a loop-back line or a question, and mention 'subscribe' at most once."),
    "reels_version": ("Instagram Reel", 100, "Vertical, 20 to 40 seconds. Casual, first line is a bold hook, short lines, end "
                      "with a save or share prompt. Add a caption of one hook line plus up to 5 hashtags."),
    "pin_version": ("Pinterest pin", 45, "Give: a pin title of up to 100 characters with the main search phrase first, a "
                    "description of up to 500 characters written for search (plain sentences, 2 or 3 keywords, a soft "
                    "call to action), and 5 to 8 words of text for the pin image."),
    "blog_version": ("blog post", 500, "A search-friendly title, a 2 line intro, 3 to 5 subheadings with short paragraphs, a "
                     "closing takeaway and a call to action. Expand the ideas with detail, don't invent facts or numbers."),
    "newsletter_version": ("newsletter paragraph", 130, "One friendly paragraph in first person, a subject line under 50 "
                           "characters and a preview line, ending with a link line such as 'Watch it here: [link]'."),
    "podcast_points": ("podcast talking points", 200, "A cold open line, 4 to 6 talking points each with one story or example "
                       "and a transition, a listener question and a sign-off. Bullets, not a word-for-word script."),
}
LIMITS = {"X post": 280, "Threads post": 500, "Bluesky post": 300, "Instagram caption": 2200, "TikTok caption": 4000,
          "YouTube title": 100, "YouTube description": 5000, "Pinterest title": 100, "Pinterest description": 800,
          "LinkedIn post": 3000}
CTAS = {"TikTok": ["Follow for part 2", "Comment your guess", "Send this to someone who needs it"],
        "YouTube Shorts": ["Subscribe for the full story", "Watch the full video on my channel", "Comment below"],
        "Instagram Reels": ["Save this for later", "Share it with a friend", "Follow for more like this"],
        "Pinterest": ["Save this pin to your board", "Click through for the full guide"],
        "X": ["Repost if this helped", "Follow for the next thread", "Reply with your own"],
        "Blog": ["Leave a comment below", "Read the next post in the series"],
        "Newsletter": ["Reply and tell me what you think", "Forward this to a friend"],
        "Podcast": ["Follow the show so you don't miss the next one", "Send in your questions"]}
GUIDE = [["TikTok", "9:16", "21 to 60 seconds", "Hook in 2 seconds, captions on, text inside the safe zone"],
         ["YouTube Shorts", "9:16", "under 60 seconds", "Loopable ending, title matters more than on TikTok"],
         ["Instagram Reels", "9:16", "15 to 45 seconds", "Cover text centred so the profile grid crop works"],
         ["Pinterest pin", "2:3", "still image or under 30 seconds", "Big readable text, keywords in the title"],
         ["X thread", "text", "5 to 10 posts", "First post is the hook, one idea per post"],
         ["Blog", "text", "400 to 800 words", "Keyword in the title, short paragraphs, subheadings"],
         ["Newsletter", "text", "100 to 300 words per item", "Subject line under 50 characters"],
         ["Podcast", "audio", "10 to 30 minutes", "Talking points, not a script"]]
POWER = {"secret", "truth", "mistake", "mistakes", "stop", "never", "why", "how", "free", "easy", "simple", "fast", "best",
         "worst", "warning", "hidden", "proven"}
LOOSE = {"the", "a", "an", "of", "to", "and", "is", "are", "was", "it", "in", "on", "for", "with", "that", "this", "you",
         "your", "i", "my", "just", "really", "very", "so", "but", "we", "they"}


def _brief(text: str, key: str, args: dict) -> str:
    label, target, style = VERSIONS[key]
    have = store.words(text)
    note = f" The script is {have} words, so cut it hard." if have > target * 1.5 else ""
    extra = f" Audience or angle: {hs.clean(args.get('angle'), 120)}." if args.get("angle") else ""
    return (f"Rewrite this script as a {label}, about {target} words.{note}{extra} {style} Keep the facts exactly as they "
            f"are, add no claims about earnings or results, and offer one alternative opening line.\n\nScript:\n{text}")


def _version(key: str):
    return lambda settings, args: _brief(store.script(args), key, args)


shorts_version, reels_version, pin_version = _version("shorts_version"), _version("reels_version"), _version("pin_version")
blog_version, newsletter_version = _version("blog_version"), _version("newsletter_version")
podcast_points = _version("podcast_points")


# ---- Series ----------------------------------------------------------------------------------------

def _tease(sentence: str) -> str:
    return " ".join(sentence.split()[:9]).rstrip(".,;:!?")


def series_split(settings: Settings, args: dict) -> screen.Shown:
    text = store.script(args)
    sentences = store.sentences(text)
    parts_n = int(hs.number(args.get("parts") or 3, "number of parts", 2, 10))
    if len(sentences) < parts_n:
        raise ValueError(f"That script only has {len(sentences)} sentences, so it can't make {parts_n} parts.")
    per_word = 60.0 / store.wpm(args)
    goal, groups, current, count = store.words(text) / parts_n, [], [], 0
    for i, s in enumerate(sentences):
        current.append(s)
        count += store.words(s)
        if len(groups) < parts_n - 1 and count >= goal and len(sentences) - i - 1 >= parts_n - 1 - len(groups):
            groups.append(current)
            current, count = [], 0
    groups.append(current)
    parts, rows = [], []
    for n, group in enumerate(groups, 1):
        nxt = groups[n][0] if n < len(groups) else ""
        recap = f"Last time: {_tease(groups[n - 2][-1])}." if n > 1 else ""
        hang = f"Part {n + 1} next: {_tease(nxt)}... and it changes everything." if nxt else "That's the end. Which part surprised you most?"
        body = " ".join(group)
        parts.append({"text": body, "recap": recap, "cliffhanger": hang})
        rows.append([str(n), str(store.words(body)), f"{store.words(body) * per_word:.0f}s", hang])
    if args.get("name"):
        saved = store.load(settings)
        saved["series"][hs.clean(args["name"], 60)] = parts
        store.save(settings, saved)
    return screen.Shown(f"Split into {len(parts)} parts, each with a cliffhanger. Reword the closing lines as you like.",
                        screen.card("table", "Series parts", "repurpose-series", columns=["Part", "Words", "Speaking", "Cliffhanger"],
                                    rows=rows))


def series_show(settings: Settings, args: dict) -> screen.Shown:
    series = store.load(settings)["series"]
    key = hs.find(series, args.get("name") or "")
    if key is None:
        if not series:
            raise ValueError("You haven't saved a split series yet. Split a script with a series name first.")
        raise ValueError("Which series? I have " + ", ".join(series) + ".")
    parts = series[key]
    if args.get("part"):
        n = int(hs.number(args["part"], "part number", 1, len(parts)))
        p = parts[n - 1]
        text = "\n\n".join(x for x in (p["recap"], p["text"], p["cliffhanger"]) if x)
        return screen.Shown(f"{key} part {n}.", screen.card("text", f"{key}, part {n}", "repurpose-part", text=text))
    items = [{"label": f"Part {i}: {store.words(p['text'])} words", "say": f"Show part {i} of the series {key}."}
             for i, p in enumerate(parts, 1)]
    return screen.Shown(f"{key} has {len(parts)} parts.", screen.card("list", key, "repurpose-series-parts", items=items))


# ---- Thread ----------------------------------------------------------------------------------------

def thread_version(settings: Settings, args: dict) -> screen.Shown:
    text = store.script(args)
    limit = int(hs.number(args.get("limit") or 280, "post length", 100, 500)) - 8
    posts, current = [], ""
    for s in store.sentences(text):
        s = s if len(s) <= limit else s[:limit - 1].rsplit(" ", 1)[0] + "..."
        if current and len(current) + 1 + len(s) > limit:
            posts.append(current)
            current = s
        else:
            current = f"{current} {s}".strip()
    posts.append(current)
    total = len(posts)
    posts = [f"{p} ({i}/{total})" for i, p in enumerate(posts, 1)]
    body = "\n\n".join(f"{p}\n[{len(p)} characters]" for p in posts)
    return screen.Shown(f"{total} posts, all inside the limit. Tighten the first one into a hook.",
                        screen.card("text", "X thread", "repurpose-thread", text=body))


# ---- Titles and thumbnails -------------------------------------------------------------------------

def titles(settings: Settings, args: dict) -> screen.Shown:
    topic = hs.need(args.get("topic"), "topic", 80)
    options = [f"{topic}: what nobody tells you", f"5 {topic} mistakes to avoid", f"How to {topic} in 60 seconds",
               f"The truth about {topic}", f"Stop doing this with {topic}", f"{topic}, explained simply",
               f"Why {topic} matters more than you think", f"{topic}: the part you were never taught"]
    rows = [[t, str(len(t)), "ok" if len(t) <= 60 else "may be cut off"] for t in options]
    return screen.Shown(f"{len(rows)} title options for {topic}. Give me more detail and I'll write sharper ones.",
                        screen.card("table", "Title options", "repurpose-titles", columns=["Title", "Length", "Fit"], rows=rows))


def title_check(settings: Settings, args: dict) -> screen.Shown:
    title = hs.need(args.get("title") or args.get("text"), "title", 200)
    limit = LIMITS.get(hs.find(LIMITS, args.get("platform") or "YouTube title") or "YouTube title", 100)
    words = re.findall(r"[a-z']+", title.lower())
    rows = [["Characters", str(len(title)), "ok" if len(title) <= 60 else "cut off in many feeds after about 60"],
            ["Hard limit", str(limit), "ok" if len(title) <= limit else "too long"],
            ["Power words", ", ".join(w for w in words if w in POWER) or "none", "add one if it suits"],
            ["Has a number", "yes" if re.search(r"\d", title) else "no", "numbers tend to help"]]
    return screen.Shown(f"{len(title)} characters against a limit of {limit}.",
                        screen.card("table", "Title check", "repurpose-titlecheck", columns=["Check", "Result", "Note"], rows=rows))


def _keys(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w'£%$]+", text) if w.lower() not in LOOSE]


def thumbnail_text(settings: Settings, args: dict) -> screen.Shown:
    words = _keys(hs.need(args.get("topic") or args.get("text"), "topic or hook", 300))
    if len(words) < 2:
        raise ValueError("Give me a few more words to work with.")
    head, tail = " ".join(words[:3]), " ".join(words[-3:])
    options = [head, tail, f"WHY {words[0]}?", f"STOP {' '.join(words[:2])}", f"{words[0]} EXPLAINED", f"THE {words[-1]} TRUTH"]
    seen, rows = set(), []
    for o in options:
        o = o.upper()
        if o not in seen:
            seen.add(o)
            rows.append([o, str(store.words(o)), str(len(o))])
    return screen.Shown(f"{len(rows)} thumbnail or cover text options, four words or fewer.",
                        screen.card("table", "Cover text", "repurpose-thumbs", columns=["Text", "Words", "Characters"], rows=rows))


def thumb_check(settings: Settings, args: dict) -> screen.Shown:
    text = hs.need(args.get("text"), "cover text", 100)
    n = store.words(text)
    rows = [["Words", str(n), "ok" if n <= 4 else "aim for 4 or fewer"],
            ["Characters", str(len(text)), "ok" if len(text) <= 25 else "long for a small thumbnail"]]
    if args.get("title"):
        same = text.lower() in hs.clean(args["title"], 200).lower()
        rows.append(["Repeats the title", "yes" if same else "no", "cover text should add to the title, not copy it" if same else "ok"])
    return screen.Shown("Cover text is fine." if n <= 4 and len(text) <= 25 else "That cover text is a bit long.",
                        screen.card("table", "Cover text check", "repurpose-thumbcheck", columns=["Check", "Result", "Note"], rows=rows))


# ---- Quotes, limits and CTAs -----------------------------------------------------------------------

def _score(s: str) -> int:
    score = 0
    if 30 <= len(s) <= 110:
        score += 3
    if re.search(r"\b(never|always|nobody|everyone|but|not|stop|only|because)\b", s, re.I):
        score += 2
    if re.search(r"\d", s):
        score += 1
    return score + (1 if s.endswith(("!", ".")) else 0)


def quote_cards(settings: Settings, args: dict) -> screen.Shown:
    text = store.script(args)
    count = int(hs.number(args.get("count") or 5, "number of quotes", 1, 15))
    ranked = sorted(store.sentences(text), key=_score, reverse=True)[:count]
    if not ranked:
        raise ValueError("I can't find any sentences in that.")
    items = [{"label": q, "say": f"Write me a shorter version of this quote card: {q[:200]}"} for q in ranked]
    return screen.Shown(f"{len(items)} quote-card lines picked from the script. Tap one to shorten it.",
                        screen.card("list", "Quote cards", "repurpose-quotes", items=items))


def char_limits(settings: Settings, args: dict) -> screen.Shown:
    rows = [[k, str(v)] for k, v in LIMITS.items()]
    return screen.Shown("Platform character limits. Apps change these, so check if it matters.",
                        screen.card("table", "Character limits", "repurpose-limits", columns=["Where", "Characters"], rows=rows))


def limits_check(settings: Settings, args: dict) -> str:
    text = store.script(args, "text to check")
    key = hs.find(LIMITS, args.get("platform") or "")
    if key is None:
        raise ValueError("Which one? " + ", ".join(LIMITS) + ".")
    over = len(text) - LIMITS[key]
    return (f"{len(text)} characters against {LIMITS[key]} for a {key}: "
            + (f"{over} too many." if over > 0 else f"fits, {-over} spare."))


def cta_swap(settings: Settings, args: dict) -> screen.Shown:
    key = hs.find(CTAS, args.get("platform") or "")
    if args.get("platform") and key is None:
        raise ValueError("Which platform? " + ", ".join(CTAS) + ".")
    rows = [[p, " / ".join(c)] for p, c in CTAS.items() if key in (None, p)]
    return screen.Shown("Calls to action that suit each platform.",
                        screen.card("table", "Calls to action", "repurpose-cta", columns=["Where", "Try"], rows=rows))


def format_guide(settings: Settings, args: dict) -> screen.Shown:
    return screen.Shown("What each format usually wants. General guidance only.",
                        screen.card("table", "Format guide", "repurpose-guide", columns=["Format", "Shape", "Length", "Tip"], rows=GUIDE))


# ---- Tool ------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "repurpose_formats",
        "description": "Turn one script into other versions (text only; no video, picture or voice is made). action: "
                       "series_split (text, parts, name) = multi-part series with cliffhanger lines / series_show "
                       "(name, part); shorts_version / reels_version / pin_version / blog_version / "
                       "newsletter_version / podcast_points (text, angle) = returns a brief, YOU write the rewrite; "
                       "thread_version (text) = X thread packed into posts; titles (topic) / title_check (title, "
                       "platform); thumbnail_text (topic) / thumb_check (text) = cover text; quote_cards (text, "
                       "count); char_limits / limits_check (text, platform); cta_swap (platform) = calls to action "
                       "per platform; format_guide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "text": {"type": "string", "description": "The script or text to work on."},
                "topic": {"type": "string"},
                "title": {"type": "string"},
                "name": {"type": "string", "description": "Series name."},
                "part": {"type": "integer"},
                "parts": {"type": "integer", "description": "How many parts, 2 to 10."},
                "angle": {"type": "string"},
                "platform": {"type": "string"},
                "count": {"type": "integer"},
                "limit": {"type": "integer", "description": "thread_version: characters per post, default 280."},
                "wpm": {"type": "number"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"repurpose_formats"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"series_split": series_split, "series_show": series_show, "shorts_version": shorts_version,
             "reels_version": reels_version, "pin_version": pin_version, "thread_version": thread_version,
             "blog_version": blog_version, "newsletter_version": newsletter_version, "podcast_points": podcast_points,
             "titles": titles, "title_check": title_check, "thumbnail_text": thumbnail_text, "thumb_check": thumb_check,
             "quote_cards": quote_cards, "char_limits": char_limits, "limits_check": limits_check, "cta_swap": cta_swap,
             "format_guide": format_guide}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
