"""A design and accessibility check-up for a web page, before it goes to a client or live.

audit_website reads one page, either a public link or an HTML file in Alfred's memory (such as a Kinetic Web Designs
site), and lists what to fix with a score out of 100. It checks the basics that are easy to miss: language, phone
viewport, title and description length, share picture and favicon, one clear H1 and headings in order, pictures with
alt text and sizes, links and buttons that say what they do, form boxes with labels, text under 12px, too many fonts,
colour pairs in the page's own CSS that fail WCAG contrast, and new-tab links without rel="noopener". It only reads
the page; it never changes it.
"""

import re
from html.parser import HTMLParser

import httpx

import memory
from config import Settings
from design_contrast import AA, colour, ratio
from design_extract import MAX_HTML, TooBig, check_url, fetch, to_hex

NAMES = {"audit_website"}
TITLE_MAX, DESCRIPTION_MAX = 60, 160
GENERIC_LINKS = {"click here", "here", "read more", "more", "learn more", "link", "this"}
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "system-ui", "inherit", "initial", "ui-sans-serif",
                 "ui-serif", "-apple-system", "blinkmacsystemfont", "emoji", "segoe ui emoji", "apple color emoji"}
NO_LABEL_NEEDED = {"hidden", "submit", "button", "reset", "image"}
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.meta, self.links, self.styles, self.inline = {}, [], [], []
        self.title, self.in_title = "", False
        self.headings, self.images, self.controls, self.blank_links = [], [], [], 0
        self.inputs, self.label_for, self.label_depth = [], set(), 0
        self.open = []  # [tag, text, attrs] for <a>/<button> being read
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if a.get("style"):
            self.inline.append(a["style"])
        if tag == "html":
            self.lang = a.get("lang", "").strip()
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link":
            self.links.append(a.get("rel", "").lower())
        elif tag == "title":
            self.in_title = True
        elif tag == "style":
            self.in_style = True
        elif re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        elif tag == "img":
            self.images.append(a)
            for item in self.open:
                item[1] += " " + a.get("alt", "")
        elif tag in ("a", "button"):
            if tag == "a" and a.get("target") == "_blank" and "noopener" not in a.get("rel", "") \
                    and "noreferrer" not in a.get("rel", ""):
                self.blank_links += 1
            self.open.append([tag, a.get("aria-label", "") or a.get("title", ""), a])
        elif tag == "label":
            self.label_depth += 1
            if a.get("for"):
                self.label_for.add(a["for"])
        elif tag in ("input", "select", "textarea"):
            if tag != "input" or a.get("type", "text").lower() not in NO_LABEL_NEEDED:
                self.inputs.append((a, self.label_depth > 0))
        elif tag == "svg":
            for item in self.open:
                item[1] += " " + a.get("aria-label", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "style":
            self.in_style = False
        elif tag == "label":
            self.label_depth = max(0, self.label_depth - 1)
        elif tag in ("a", "button"):
            for i in range(len(self.open) - 1, -1, -1):
                if self.open[i][0] == tag:
                    self.controls.append((tag, " ".join(self.open.pop(i)[1].split())))
                    break

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_style:
            self.styles.append(data)
        for item in self.open:
            item[1] += " " + data


def css_checks(css: str) -> tuple[list[str], list[str]]:
    """(contrast failures, small text) from rules that set both colours as plain colours."""
    failures, small = [], []
    for selector, body in RULE.findall(css):
        decls = {k.strip().lower(): v.strip() for k, v in re.findall(r"([\w-]+)\s*:\s*([^;]+)", body)}
        fg = decls.get("color")
        bg = decls.get("background-color") or decls.get("background")
        selector = " ".join(selector.split())[:40]
        if fg and bg:
            f = b = ""
            first = re.split(r"\s", bg.strip())[0]
            if len(to_hex(first)) == 7:  # a solid colour; skip variables, gradients, pictures and see-through ones
                try:
                    f, b = colour(fg), colour(first)
                except ValueError:
                    pass
            if f and b and ratio(f, b) < AA:
                failures.append(f"{selector} ({f} on {b}, {ratio(f, b):.1f}:1)")
        size = re.fullmatch(r"([\d.]+)px", decls.get("font-size", ""))
        if size and float(size.group(1)) < 12:
            small.append(f"{selector} ({size.group(1)}px)")
    return failures, small


def font_families(css: str) -> set[str]:
    found = set()
    for stack in re.findall(r"font-family\s*:\s*([^;}]+)", css, re.I):
        first = stack.split(",")[0].strip().strip("'\"").lower()
        if first and first not in GENERIC_FONTS and not first.startswith("var("):
            found.add(first)
    return found


def audit(markup: str) -> dict:
    page = Page()
    page.feed(markup)
    css = "\n".join(page.styles) + "\n" + "\n".join(f"x{{{s}}}" for s in page.inline)
    fix, tips = [], []
    if not page.lang:
        fix.append('Add a language to <html>, e.g. lang="en-GB", so screen readers speak it properly.')
    if "viewport" not in page.meta:
        fix.append('Add <meta name="viewport" content="width=device-width, initial-scale=1"> or it looks tiny on '
                   "phones.")
    title = " ".join(page.title.split())
    if not title:
        fix.append("Give the page a <title>; it's the name in Google and on the browser tab.")
    elif len(title) > TITLE_MAX:
        tips.append(f"The title is {len(title)} letters; Google cuts it after about {TITLE_MAX}.")
    description = page.meta.get("description", "").strip()
    if not description:
        fix.append("Add a meta description (one or two sentences) for Google results.")
    elif len(description) > DESCRIPTION_MAX:
        tips.append(f"The description is {len(description)} letters; about {DESCRIPTION_MAX} show in Google.")
    if not page.meta.get("og:image", "").strip():
        tips.append("No share picture (og:image), so links look bare on WhatsApp and Facebook; make_share_card can "
                    "make one.")
    if not any("icon" in rel for rel in page.links):
        tips.append("No favicon for the browser tab; make_logo makes favicon.svg.")
    h1 = page.headings.count(1)
    if h1 == 0:
        fix.append("There's no H1; give the page one main heading.")
    elif h1 > 1:
        tips.append(f"There are {h1} H1 headings; one main heading reads clearer for Google and screen readers.")
    skips = sorted({f"H{a} to H{b}" for a, b in zip(page.headings, page.headings[1:]) if b > a + 1})
    if skips:
        tips.append("Headings skip a level (" + ", ".join(skips) + "); go down one step at a time.")
    no_alt = sum(1 for img in page.images if "alt" not in img)
    if no_alt:
        fix.append(f"{no_alt} picture{'s have' if no_alt > 1 else ' has'} no alt text; describe them, or use alt=\"\" "
                   "for decoration.")
    no_size = sum(1 for img in page.images if not (img.get("width") and img.get("height")))
    if no_size:
        tips.append(f"{no_size} picture{'s' if no_size > 1 else ''} without width and height, so the page jumps "
                    "while loading.")
    empty = [tag for tag, text in page.controls if not text]
    if empty:
        fix.append(f"{len(empty)} link{'s or buttons' if len(empty) > 1 else ' or button'} with no words; add text "
                   "or an aria-label so people know where it goes.")
    vague = sorted({text for tag, text in page.controls if tag == "a" and text.lower().strip(".!") in GENERIC_LINKS})
    if vague:
        tips.append("Vague link words (" + ", ".join(f'"{v}"' for v in vague) + "); say where the link goes.")
    unlabelled = sum(1 for a, inside in page.inputs
                     if not inside and a.get("id", "") not in page.label_for and not a.get("aria-label"))
    if unlabelled:
        fix.append(f"{unlabelled} form box{'es' if unlabelled > 1 else ''} without a label; placeholders alone "
                   "vanish when typing.")
    failures, small = css_checks(css)
    if failures:
        fix.append("Text that's hard to read (below 4.5:1): " + "; ".join(failures[:5])
                   + (f" and {len(failures) - 5} more" if len(failures) > 5 else "") + ". check_contrast can fix it.")
    if small:
        tips.append("Text under 12px: " + "; ".join(small[:5]) + ".")
    fonts = font_families(css)
    if len(fonts) > 3:
        tips.append(f"{len(fonts)} different fonts ({', '.join(sorted(fonts))}); two or three looks more polished.")
    if page.blank_links:
        tips.append(f'{page.blank_links} new-tab link{"s" if page.blank_links > 1 else ""} without rel="noopener"; '
                    "add it for safety.")
    score = max(0, 100 - 10 * len(fix) - 3 * len(tips))
    return {"title": title, "score": score, "fix": fix, "tips": tips}


def report(found: dict, where: str) -> str:
    lines = [f"Design check-up for {where}: {found['score']}/100."]
    if found["fix"]:
        lines += ["Fix:"] + [f"- {item}" for item in found["fix"]]
    if found["tips"]:
        lines += ["Nice to have:"] + [f"- {item}" for item in found["tips"]]
    if not found["fix"] and not found["tips"]:
        lines.append("Nothing to fix: the basics are all in place.")
    lines.append("(This reads the page's HTML and its own <style> CSS; linked stylesheets aren't checked.)")
    return "\n".join(lines)


async def read_page(args: dict, settings: Settings, http: httpx.AsyncClient) -> tuple[str, str]:
    if args.get("url"):
        url = check_url(args["url"])
        try:
            final, kind, markup = await fetch(http, url, MAX_HTML)
        except TooBig:
            raise ValueError("That page is too big for me to read.") from None
        if kind and "html" not in kind:
            raise ValueError("That link isn't a web page.")
        return markup, final
    if not args.get("folder"):
        raise ValueError("Give a website link, or the memory folder and file of the page to check.")
    path = memory.file_path(settings, str(args["folder"]), str(args.get("file") or "index.html"))
    if path.suffix.lower() not in (".html", ".htm"):
        raise ValueError("Pick an .html file to check.")
    if path.stat().st_size > MAX_HTML:
        raise ValueError("That page is too big for me to read.")
    return path.read_text(encoding="utf-8", errors="replace"), path.relative_to(memory.root(settings)).as_posix()


def tool_definitions() -> list[dict]:
    return [{
        "name": "audit_website",
        "description": "Give a web page a design and accessibility check-up with a score out of 100: language, phone "
                       "viewport, title and description length, share picture, favicon, headings, picture alt text "
                       "and sizes, link and button wording, form labels, small text, too many fonts and colour "
                       "contrast in the page's own CSS. Reads a public link or an HTML file in memory (e.g. a Kinetic "
                       "Web Designs site) and never changes it. Use before showing a client a site or putting it "
                       "live; say the fixes in plain words, most important first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Public page to check, e.g. kineticwebdesigns.co.uk."},
                "folder": {"type": "string", "description": "Memory folder holding the page, e.g. 'Kinetic Web "
                                                            "Designs/Lebo's Bakery'."},
                "file": {"type": "string", "description": "HTML file in that folder (default index.html)."},
            },
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient | None = None) -> str:
    if http is None and args.get("url"):
        async with httpx.AsyncClient() as own:
            return await run_tool(name, args, settings, own)
    try:
        markup, where = await read_page(args, settings, http)
        return report(audit(markup), where)
    except (TypeError, ValueError) as e:
        return str(e)
