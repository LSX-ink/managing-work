"""Reading help, part 1: turning a web page, pasted words or a text file into clean paragraphs.

A page is fetched with webview_common.get_public (which re-checks the link is public after every redirect), then
read with the standard html.parser: menus, adverts, cookie banners, forms and scripts are left out, and the
headings, paragraphs, pictures and links that are left come back in order. Nothing is run and nothing is sent.
"""

import html
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

import memory
import screen
import webview_common as web
from config import Settings

MAX_CHARS = 150_000
VOID = {"img", "br", "hr", "input", "meta", "link", "source", "area", "base", "col", "embed", "wbr", "param", "track"}
HARD_SKIP = {"script", "style", "noscript", "svg", "template", "head", "iframe", "canvas", "object", "select"}
SOFT_SKIP = {"nav", "header", "footer", "aside", "form", "dialog", "button"}
BLOCKS = {"p", "div", "section", "article", "main", "li", "ul", "ol", "blockquote", "tr", "td", "th", "table", "pre",
          "figure", "figcaption", "dd", "dt", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr"}
NOISE = re.compile(r"cookie|consent|gdpr|banner|advert|(^|[-_ ])ads?([-_ ]|$)|sponsor|promo|newsletter|subscribe|popup|"
                   r"modal|sidebar|share|social|breadcrumb|comment|related|widget|skip", re.I)
BOILERPLATE = re.compile(r"accept (all )?cookies|we use cookies|sign up for our newsletter|all rights reserved|"
                         r"subscribe to (our|the)|advertisement", re.I)
MARKDOWN_HEAD = re.compile(r"^(#{1,6})\s+(.*)$")


class _Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool, bool, bool]] = []  # tag, hard skip, soft skip, in main
        self.hard = self.soft = self.main = 0
        self.blocks: list[dict] = []
        self.images: list[dict] = []
        self.links: list[dict] = []
        self.title = ""
        self.lang = ""
        self.kind = "p"
        self.buf: list[str] = []
        self.buf_main = False
        self.in_title = False
        self.link: dict | None = None

    def flush(self):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if text:
            self.blocks.append({"k": self.kind, "t": text, "main": self.buf_main})

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = (a.get("lang") or "")[:10]
        if tag == "title":
            self.in_title = True
        if tag == "img":
            self.image(a)
            return
        if tag in VOID:
            if tag in BLOCKS:
                self.flush()
            return
        label = f"{a.get('class') or ''} {a.get('id') or ''}"
        hidden = "hidden" in a or (a.get("aria-hidden") or "").lower() == "true"
        role = (a.get("role") or "").lower()
        hard = tag in HARD_SKIP or hidden
        soft = tag in SOFT_SKIP or bool(NOISE.search(label)) or role in {"navigation", "banner", "complementary", "dialog"}
        main = tag in ("article", "main") or role == "main"
        self.stack.append((tag, hard, soft, main))
        self.hard += hard
        self.soft += soft
        self.main += main
        if tag in BLOCKS:
            self.flush()
            self.kind = tag if re.fullmatch(r"h[1-6]", tag) else ("li" if tag == "li" else "p")
            self.buf_main = self.main > 0
        if tag == "a" and not self.hard and a.get("href"):
            self.link = {"href": a["href"], "text": [], "menu": self.soft > 0}

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "a" and self.link is not None:
            text = re.sub(r"\s+", " ", "".join(self.link["text"])).strip()
            if text:
                self.links.append({"href": self.link["href"], "text": text[:150], "menu": self.link["menu"]})
            self.link = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for _, hard, soft, main in self.stack[i:]:
                    self.hard -= hard
                    self.soft -= soft
                    self.main -= main
                del self.stack[i:]
                break
        else:
            return
        if tag in BLOCKS:
            self.flush()
            self.kind = "p"
            self.buf_main = self.main > 0

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.hard:
            return
        if self.link is not None:
            self.link["text"].append(data)
        if not self.soft:
            self.buf.append(data)

    def image(self, a):
        if self.hard or self.soft:
            return
        src = a.get("src") or a.get("data-src") or ""
        if not src or src.startswith("data:"):
            return
        w, h = str(a.get("width") or "").rstrip("px"), str(a.get("height") or "").rstrip("px")
        if (w.isdigit() and int(w) < 40) or (h.isdigit() and int(h) < 40):
            return
        role = (a.get("role") or "").lower()
        self.images.append({"src": src, "alt": re.sub(r"\s+", " ", a.get("alt") or "").strip()[:300],
                            "decorative": role in ("presentation", "none") or a.get("alt") == ""})


def keep(block: dict) -> bool:
    text = block["t"]
    if BOILERPLATE.search(text) and len(text) < 160:
        return False
    if block["k"].startswith("h"):
        return len(text) >= 2
    return len(text) >= (25 if block["k"] == "li" else 40)


def absolute(base: str, link: str) -> str:
    return urljoin(base, html.unescape(link)) if base else link


def parse_html(markup: str, base_url: str = "") -> dict:
    """{title, lang, blocks: [{k, t}], images, links} from page HTML, with the main article's text preferred."""
    parser = _Reader()
    parser.feed(markup[:web.MAX_PAGE])
    parser.close()
    parser.flush()
    blocks = [b for b in parser.blocks if keep(b)]
    main = [b for b in blocks if b["main"]]
    if sum(len(b["t"]) for b in main) >= 300:
        blocks = main
    out, seen, total = [], set(), 0
    for b in blocks:
        if b["t"] in seen:
            continue
        seen.add(b["t"])
        total += len(b["t"])
        if total > MAX_CHARS:
            break
        out.append({"k": b["k"], "t": b["t"]})
    h1 = next((b["t"] for b in out if b["k"] == "h1"), "")
    links = [dict(x, href=absolute(base_url, x["href"])) for x in parser.links[:400]
             if not x["href"].startswith(("#", "javascript:", "mailto:", "tel:"))]
    return {"title": web.clean(parser.title, 150) or h1, "lang": parser.lang, "blocks": out,
            "images": [dict(i, src=absolute(base_url, i["src"])) for i in parser.images[:100]], "links": links}


def plain_markdown(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(\*\*|__|\*|_|`)", "", text)
    return re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", text).strip()


def parse_text(text: str) -> list[dict]:
    """Paragraphs (and Markdown headings) from plain text: blank lines separate paragraphs."""
    blocks = []
    for chunk in re.split(r"\n\s*\n", str(text).replace("\r\n", "\n")):
        lines = [x.strip() for x in chunk.split("\n") if x.strip()]
        if not lines:
            continue
        head = MARKDOWN_HEAD.match(lines[0])
        if head:
            blocks.append({"k": f"h{len(head.group(1))}", "t": plain_markdown(head.group(2))})
            lines = lines[1:]
        if lines:
            blocks.append({"k": "p", "t": plain_markdown(" ".join(lines))})
    return [b for b in blocks if b["t"]][:2000]


async def fetch_page(http: httpx.AsyncClient, url: str) -> dict:
    """A public web page as {title, site, url, lang, blocks, images, links}; friendly ValueError if it can't be read."""
    r = await web.get_public(http, url)
    final = str(r.url)
    kind = r.headers.get("content-type", "text/html").lower()
    if "html" in kind:
        page = parse_html(r.text, final)
    elif kind.startswith("text/"):
        page = {"title": "", "lang": "", "blocks": parse_text(r.text[:MAX_CHARS]), "images": [], "links": []}
    else:
        raise ValueError("That link isn't a web page or a text file, so I can't read it out.")
    if not page["blocks"]:
        raise ValueError("I couldn't find any readable words on that page.")
    host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", final).split("/")[0])
    return dict(page, url=final, site=host, title=page["title"] or host)


def read_file(settings: Settings, folder: str, filename: str) -> dict:
    """A .txt or .md file in the memory folders as {title, site, url, blocks, file}."""
    path = screen.find_file(settings, str(folder or ""), str(filename or ""))
    if path.suffix.lower() not in {".txt", ".md"}:
        raise ValueError(f"I can read .txt and .md files aloud, not {path.suffix or 'that kind of'} files"
                         " (a PDF has no plain text I can pull out).")
    if path.stat().st_size > memory.MAX_FILE_BYTES:
        raise ValueError("That file is too big to read out.")
    blocks = parse_text(path.read_text(encoding="utf-8", errors="replace")[:MAX_CHARS])
    if not blocks:
        raise ValueError(f"{path.name} is empty.")
    rel = path.resolve().relative_to(memory.root(settings).resolve())
    return {"title": path.stem, "site": path.parent.name, "url": "", "lang": "", "blocks": blocks, "images": [],
            "links": [], "folder": rel.parent.as_posix() if rel.parent.as_posix() != "." else "", "filename": path.name}


async def source(settings: Settings, http: httpx.AsyncClient, args: dict) -> dict:
    """The words to work on: a link (url), pasted words (text) or a memory file (folder + filename)."""
    if str(args.get("url") or "").strip():
        return await fetch_page(http, args["url"])
    if str(args.get("text") or "").strip():
        return {"title": web.clean(args.get("title"), 80) or "Your text", "site": "", "url": "", "lang": "",
                "blocks": parse_text(str(args["text"])[:MAX_CHARS]), "images": [], "links": []}
    if str(args.get("filename") or "").strip():
        return read_file(settings, args.get("folder") or "", args["filename"])
    raise ValueError("Give me a web link, some pasted text, or the name of a text file to read.")


def plain(blocks: list[dict]) -> str:
    return "\n\n".join(b["t"] for b in blocks)


def words_in(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'’-]*", text)
