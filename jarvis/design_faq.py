"""FAQ sections: the "questions people ask" block that answers buyers before they message, and helps on Google.

make_faq_section turns 2 to 15 questions and answers into a paste-in HTML block in the brand colour: each question is
a real <details>/<summary> disclosure, so it opens with a tap, a click, Enter or Space, works with screen readers and
needs no JavaScript. A plus sign turns into a minus when open, the first question can start open, and an optional
"Still stuck?" line links to the contact page. It also writes schema.org FAQPage data so search engines can read the
questions and answers. Answers are plain text; a blank line starts a new paragraph and web addresses become links.
Saves faq.html in Kinetic Web Designs/<name>/web, plus faq-preview.html (the block on a page) to check it.
"""

import html
import json
import re

import memory
from config import Settings
from design_contrast import AA, UI, colour, fix, ratio
from design_extract import FOLDER

NAMES = {"make_faq_section"}
MIN_QA, MAX_QA = 2, 15
URL = re.compile(r"https://[^\s<>\"']+[^\s<>\"'.,;:!?)]")


def answer_html(text: str) -> str:
    """Plain text to safe HTML paragraphs, with https links made clickable."""
    out = []
    for para in re.split(r"\n\s*\n", text.strip()):
        para = " ".join(para.split())
        parts, last = [], 0
        for m in URL.finditer(para):
            parts.append(html.escape(para[last:m.start()]))
            url = html.escape(m.group(0))
            parts.append(f'<a href="{url}">{url}</a>')
            last = m.end()
        parts.append(html.escape(para[last:]))
        out.append(f"<p>{''.join(parts)}</p>")
    return "".join(out)


def schema(items: list[tuple[str, str]]) -> str:
    data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": " ".join(a.split())}}
        for q, a in items]}
    return json.dumps(data, indent=2, ensure_ascii=False).replace("</", "<\\/")


def block(name: str, brand: str, title: str, items: list[tuple[str, str]], first_open: bool, contact: str) -> str:
    e = html.escape
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    ring = brand if ratio(brand, "#ffffff") >= UI else fix(brand, "#ffffff", UI)
    rows = "\n".join(
        f'  <details{" open" if first_open and i == 0 else ""}>\n    <summary>{e(q)}</summary>\n'
        f'    <div class="faq-a">{answer_html(a)}</div>\n  </details>' for i, (q, a) in enumerate(items))
    more = (f'\n  <p class="faq-more">Still stuck? <a href="{e(contact)}">Get in touch</a> and we\'ll help.</p>'
            if contact else "")
    return f"""<!-- FAQ for {e(name)}: paste this block where the questions should show. -->
<section class="faq" aria-labelledby="faq-title" style="--faq-accent:{accent};--faq-ring:{ring}">
  <style>
    .faq {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; max-width: 46rem;
           margin: 0 auto; color: #18181b; }}
    .faq h2 {{ font-size: clamp(1.5rem, 4vw, 2rem); margin: 0 0 1rem; }}
    .faq details {{ border-bottom: 1px solid #e4e4e7; }}
    .faq details:first-of-type {{ border-top: 1px solid #e4e4e7; }}
    .faq summary {{ list-style: none; cursor: pointer; display: flex; justify-content: space-between; gap: 1rem;
                   align-items: center; padding: 1.1rem .25rem; font-weight: 650; font-size: 1.05rem;
                   min-height: 44px; }}
    .faq summary::-webkit-details-marker {{ display: none; }}
    .faq summary::after {{ content: "+"; flex: none; width: 1.75rem; height: 1.75rem; border-radius: 50%;
                          display: grid; place-items: center; font-size: 1.25rem; line-height: 1;
                          color: var(--faq-accent); border: 2px solid var(--faq-ring); }}
    .faq details[open] summary::after {{ content: "−"; }}
    .faq summary:hover {{ color: var(--faq-accent); }}
    .faq summary:focus-visible {{ outline: 3px solid var(--faq-accent); outline-offset: 2px; border-radius: 6px; }}
    .faq-a {{ padding: 0 .25rem 1.1rem; color: #3f3f46; line-height: 1.6; }}
    .faq-a p {{ margin: 0 0 .75rem; }}
    .faq-a p:last-child {{ margin: 0; }}
    .faq a {{ color: var(--faq-accent); }}
    .faq-more {{ margin: 1.25rem 0 0; color: #52525b; }}
    @media (prefers-reduced-motion: no-preference) {{
      .faq details[open] .faq-a {{ animation: faq-in .2s ease-out; }}
    }}
    @keyframes faq-in {{ from {{ opacity: 0; transform: translateY(-4px); }} }}
  </style>
  <h2 id="faq-title">{e(title)}</h2>
{rows}{more}
  <script type="application/ld+json">
{schema(items)}
  </script>
</section>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the FAQ.")
    brand = colour(args.get("colour") or "")
    raw = args.get("questions") or []
    if not isinstance(raw, list):
        raise ValueError("Give the questions as a list of {question, answer}.")
    items = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each item needs a question and an answer.")
        q = clean(item.get("question"))
        a = str(item.get("answer") or "").strip()
        if not q or not a:
            raise ValueError("Each item needs a question and an answer.")
        if len(q) > 160 or len(a) > 1500:
            raise ValueError(f"Keep '{q[:40]}...' shorter: questions under 160 letters, answers under 1500.")
        items.append((q, a))
    if not MIN_QA <= len(items) <= MAX_QA:
        raise ValueError(f"Give {MIN_QA} to {MAX_QA} questions (more than that is hard to scan).")
    dupes = {q.lower() for q, _ in items if [x.lower() for x, _ in items].count(q.lower()) > 1}
    if dupes:
        raise ValueError(f"These questions are there twice: {', '.join(sorted(dupes))}.")
    title = clean(args.get("title")) or "Questions people ask"
    contact = clean(args.get("contact_url"))
    if contact and not re.match(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*|mailto:[^\s\"'<>]+|tel:[\d+ ()-]+)$", contact):
        raise ValueError("Give the contact link as https://..., /contact, mailto: or tel:.")
    code = block(name, brand, title, items, args.get("first_open", True) is not False, contact)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | FAQ</title>\n"
               "</head>\n<body style=\"margin:0;padding:48px 20px;background:#fff\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "faq.html").write_text(code, encoding="utf-8")
    (path / "faq-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made an FAQ section for {name} with {len(items)} questions in {where}: faq.html to paste into the "
            "page, and faq-preview.html to check it. Each question opens with a tap or the keyboard, no JavaScript "
            "needed, and it carries FAQ data so Google can read the questions. Only put each question on one page "
            "of the site.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_faq_section",
        "description": "Make a paste-in FAQ section for a client site in the brand colour: 2-15 questions as "
                       "accessible open/close rows (no JavaScript), plus/minus icons, optional 'still stuck?' "
                       "contact link, and schema.org FAQPage data for Google. Saves faq.html and faq-preview.html in "
                       "Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "title": {"type": "string", "description": "Heading (default 'Questions people ask')."},
                "questions": {"type": "array", "description": "2-15 items, most asked first.", "items": {
                    "type": "object", "properties": {"question": {"type": "string"}, "answer": {"type": "string"}},
                    "required": ["question", "answer"]}},
                "first_open": {"type": "boolean", "description": "Start with the first answer open (default yes)."},
                "contact_url": {"type": "string", "description": "Link for 'Still stuck?', e.g. /contact."},
            },
            "required": ["name", "colour", "questions"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
