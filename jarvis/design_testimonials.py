"""Testimonials sections: real customer reviews shown on the website as tidy cards, the proof that makes people book.

make_testimonials_section turns 1 to 9 reviews into a paste-in HTML block in the brand colour: a heading, an optional
summary line ("4.9 from 120 Google reviews", with a link to see them all), and a grid of cards, each with the stars
(drawn as inline SVG so they look the same everywhere, with half stars, and read out as "Rated 4.5 out of 5"), the
words, the reviewer's name as they want it shown and where the review came from. Long reviews get a "Read more" that
opens with no JavaScript. Cards sit three across on a laptop and stack on a phone. It deliberately adds no review
star data for Google: Google ignores stars a business adds about itself, and can penalise it. Only use reviews
customers really wrote, with their say-so. Saves testimonials.html and testimonials-preview.html in
Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, UI, colour, fix, ratio
from design_extract import FOLDER

NAMES = {"make_testimonials_section"}
MAX_REVIEWS, SHORT = 9, 260
GOLD, EMPTY = "#f59e0b", "#d4d4d8"
STAR = "M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z"


def stars_svg(rating: float, uid: str) -> str:
    """Five SVG stars; a half star is half gold via a gradient. Hidden from screen readers (the label says it)."""
    parts = []
    for i in range(5):
        fill = max(0.0, min(1.0, rating - i))
        x = i * 24
        if fill in (0.0, 1.0):
            parts.append(f'<path transform="translate({x})" d="{STAR}" fill="{GOLD if fill else EMPTY}"/>')
        else:
            gid = f"{uid}-h{i}"
            parts.append(f'<linearGradient id="{gid}"><stop offset="{fill:.2f}" stop-color="{GOLD}"/>'
                         f'<stop offset="{fill:.2f}" stop-color="{EMPTY}"/></linearGradient>'
                         f'<path transform="translate({x})" d="{STAR}" fill="url(#{gid})"/>')
    return (f'<svg class="t-stars" viewBox="0 0 120 24" width="100" height="20" aria-hidden="true">'
            f'{"".join(parts)}</svg>')


def say(rating: float) -> str:
    return f"Rated {rating:g} out of 5"


def card(i: int, r: dict) -> str:
    e = html.escape
    words = r["quote"]
    if len(words) > SHORT:
        cut = words[:SHORT]
        end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        # end at a sentence if one ends late enough, so the rest reads as its own paragraph when opened
        cut = cut[:end + 1] if end > SHORT * 0.5 else cut.rsplit(" ", 1)[0].rstrip(",;:-")
        body = (f'<p>“{e(cut)}<span class="t-dots">…</span></p><details><summary>Read more<span class="t-sr"> of '
                f'{e(r["who"])}\'s review</span></summary><p>{e(words[len(cut):].lstrip())}”</p></details>')
    else:
        body = f"<p>“{e(words)}”</p>"
    source = f'<span class="t-src">{e(r["source"])}</span>' if r["source"] else ""
    return (f'  <figure class="t-card">\n    <p class="t-rating"><span class="t-sr">{say(r["stars"])}</span>'
            f'{stars_svg(r["stars"], f"t{i}")}</p>\n    <blockquote>{body}</blockquote>\n'
            f'    <figcaption><strong>{e(r["who"])}</strong>{source}</figcaption>\n  </figure>')


def block(name: str, brand: str, title: str, summary: str, link: str, reviews: list[dict]) -> str:
    e = html.escape
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    mark = brand if ratio(brand, "#ffffff") >= UI else fix(brand, "#ffffff", UI)
    more = f' <a href="{e(link)}">See all reviews</a>' if link else ""
    top = f'<p class="t-summary">{e(summary)}{more}</p>' if summary or link else ""
    cards = "\n".join(card(i, r) for i, r in enumerate(reviews))
    return f"""<!-- Customer reviews for {e(name)}: paste this block where the reviews should show. -->
<section class="testimonials" aria-labelledby="t-title" style="--t-accent:{accent};--t-mark:{mark}">
  <style>
    .testimonials {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #18181b;
                    max-width: 72rem; margin: 0 auto; padding: 0 1rem; }}
    .testimonials h2 {{ text-align: center; font-size: clamp(1.75rem, 4.5vw, 2.5rem); margin: 0 0 .5rem; }}
    .t-summary {{ text-align: center; color: #52525b; margin: 0 0 2rem; }}
    .t-summary a, .testimonials summary {{ color: var(--t-accent); font-weight: 600; }}
    .t-grid {{ display: grid; gap: 1.25rem; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
              align-items: start; }}
    .t-card {{ margin: 0; background: #fff; border: 1px solid #e4e4e7; border-radius: 1.25rem; padding: 1.5rem;
              position: relative; box-shadow: 0 6px 20px rgb(0 0 0 / .05); }}
    .t-card::before {{ content: "“"; position: absolute; right: 1.25rem; top: .25rem; font: 800 4.5rem/1 Georgia,
                      serif; color: var(--t-mark); opacity: .25; }}
    .t-rating {{ margin: 0 0 .75rem; line-height: 0; }}
    .testimonials blockquote {{ margin: 0 0 1rem; line-height: 1.6; color: #27272a; }}
    .testimonials blockquote p {{ margin: 0; display: inline; }}
    .testimonials details p {{ display: block; margin-top: .6rem; }}
    .testimonials details {{ display: inline; }}
    .testimonials details[open] summary, .t-card:has(details[open]) .t-dots {{ display: none; }}
    .testimonials summary {{ cursor: pointer; list-style: none; display: inline-block; margin-left: .35rem; }}
    .testimonials summary::-webkit-details-marker {{ display: none; }}
    .testimonials summary:focus-visible, .t-summary a:focus-visible {{ outline: 3px solid var(--t-accent);
                    outline-offset: 2px; border-radius: 4px; }}
    .testimonials figcaption {{ display: flex; flex-direction: column; padding-top: .9rem;
                               border-top: 1px solid #f4f4f5; }}
    .t-src {{ color: #52525b; font-size: .9rem; }}
    .t-sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);
            white-space: nowrap; }}
  </style>
  <h2 id="t-title">{e(title)}</h2>
  {top}
  <div class="t-grid">
{cards}
  </div>
</section>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the reviews section.")
    brand = colour(args.get("colour") or "")
    raw = args.get("reviews") or []
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_REVIEWS:
        raise ValueError(f"Give 1 to {MAX_REVIEWS} reviews (3 or 6 fill the rows neatly).")
    reviews = []
    for r in raw:
        if not isinstance(r, dict):
            raise ValueError("Each review needs the words and the reviewer's name.")
        quote = clean(r.get("quote")).strip("\"'“”")
        who = clean(r.get("reviewer"))[:60]
        if not quote or not who:
            raise ValueError("Each review needs the words and the reviewer's name, e.g. 'Sarah K.'.")
        if len(quote) > 1200:
            raise ValueError(f"{who}'s review is very long; pick the best few sentences.")
        stars = float(r.get("stars") if r.get("stars") is not None else 5)
        if not 1 <= stars <= 5 or stars * 2 != int(stars * 2):
            raise ValueError("Stars go from 1 to 5, in halves (e.g. 4.5).")
        reviews.append({"quote": quote, "who": who, "stars": stars, "source": clean(r.get("source"))[:40]})
    link = clean(args.get("reviews_url"))
    if link and not re.match(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*)$", link):
        raise ValueError("Give the link to all reviews as a https:// address or a path.")
    title = clean(args.get("title")) or "What our customers say"
    code = block(name, brand, title, clean(args.get("summary"))[:120], link, reviews)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Reviews</title>\n"
               "</head>\n<body style=\"margin:0;padding:56px 0;background:#fafafa\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "testimonials.html").write_text(code, encoding="utf-8")
    (path / "testimonials-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    long_ones = sum(len(r["quote"]) > SHORT for r in reviews)
    return (f"Made a reviews section for {name} with {len(reviews)} review{'s' if len(reviews) != 1 else ''} in "
            f"{where}: testimonials.html to paste into the page and testimonials-preview.html to check it."
            + (f" {long_ones} long review{'s get' if long_ones != 1 else ' gets'} a 'Read more'." if long_ones else "")
            + " Only use reviews customers really wrote, with their OK to share.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_testimonials_section",
        "description": "Make a paste-in customer reviews section for a website in the brand colour: heading, "
                       "optional summary line with a 'See all reviews' link, and 1-9 cards with SVG stars (half "
                       "stars, read aloud as 'Rated 4.5 out of 5'), the quote, reviewer name and source; long ones "
                       "get 'Read more'. No JavaScript. Saves testimonials.html and a preview in "
                       "Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "title": {"type": "string", "description": "Heading (default 'What our customers say')."},
                "summary": {"type": "string", "description": "e.g. '4.9 from 120 Google reviews'."},
                "reviews_url": {"type": "string", "description": "Link to all reviews (Google, Trustpilot...)."},
                "reviews": {"type": "array", "description": "1-9 real reviews.", "items": {
                    "type": "object", "properties": {
                        "quote": {"type": "string"}, "reviewer": {"type": "string"},
                        "stars": {"type": "number", "description": "1-5 in halves (default 5)."},
                        "source": {"type": "string", "description": "e.g. 'Google review'."}},
                    "required": ["quote", "reviewer"]}},
            },
            "required": ["name", "colour", "reviews"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
