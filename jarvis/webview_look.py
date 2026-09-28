"""The web on the Alfred screen: news headlines to click and read, Wikipedia articles, book covers, link previews,
web pictures to keep, web pages saved as notes, and dog or cat pictures. Nothing opens the web browser.

Builds on feeds.py (BBC sections, Wikipedia) and screen.read_page (the reader window).
"""

import re
from urllib.parse import quote, urljoin, urlparse

import httpx

import feeds
import memory
import screen
import webview_common as web
from config import Settings

screen.EXTRA_KINDS.update({"webcard", "webgallery"})

OPEN_LIBRARY = "https://openlibrary.org/search.json"
COVERS = "https://covers.openlibrary.org/b/id/{}-M.jpg"
DOG = "https://dog.ceo/api"
CAT = "https://api.thecatapi.com/v1/images/search"
ACTIONS = ["news", "wikipedia", "books", "link_preview", "image", "page_to_note", "dog", "cat"]


def read_say(url: str) -> str:
    return f"Read me the page {url} on screen."


async def news(http: httpx.AsyncClient, section: str) -> screen.Shown:
    section = section if section in feeds.SECTIONS else "top"
    r = await feeds.fetch(http, feeds.BBC + feeds.SECTIONS[section], "BBC News")
    _, items = web.parse_feed(r.text)
    items = [i for i in items if i["link"].startswith("https://")][:15]
    if not items:
        return screen.Shown(f"The BBC {section} feed is empty right now.", screen.card("text", "BBC News", text="Nothing yet."))
    label = "top stories" if section == "top" else f"{section} headlines"
    card = screen.card("list", f"BBC {label}", "webview-news", items=[
        {"label": i["title"], "say": read_say(i["link"])} for i in items],
        buttons=[{"label": "Refresh", "say": f"Show me the BBC {section} news on screen."}])
    return screen.Shown(f"The BBC {label} are on the screen; tap one to read it. Top three: "
                        + "; ".join(i["title"] for i in items[:3]) + ".", card)


async def wikipedia(http: httpx.AsyncClient, topic: str) -> screen.Shown:
    topic = web.need(topic, "topic", 200)
    body = await web.get_json(http, f"{feeds.WIKI}/page/summary/{quote(topic.replace(' ', '_'), safe='')}", "Wikipedia",
                              missing=f"Wikipedia has no page called {topic}.")
    if body.get("type") == "disambiguation":
        raise ValueError(f"'{body.get('title')}' could mean several things on Wikipedia. Ask about a more specific topic.")
    url = web.https(((body.get("content_urls") or {}).get("desktop") or {}).get("page"))
    image = web.https((body.get("originalimage") or body.get("thumbnail") or {}).get("source"))
    title = web.clean(body.get("title"), 120) or topic
    text = web.clean(body.get("extract"), 3000) or "Wikipedia has no summary for it."
    buttons = [{"label": "Read full article", "say": read_say(url)}] if url else []
    card = screen.card("reader", title, f"webview-wiki-{title}", url=url, text=text, image=image, site="Wikipedia",
                       buttons=buttons)
    return screen.Shown(f"{title} from Wikipedia is on the screen. {web.clean(text, 500)}", card)


async def books(http: httpx.AsyncClient, query: str) -> screen.Shown:
    query = web.need(query, "book or author", 120)
    body = await web.get_json(http, OPEN_LIBRARY, "Open Library", {
        "q": query, "limit": 12, "fields": "key,title,author_name,first_publish_year,cover_i"})
    tiles = []
    for doc in (body.get("docs") or [])[:12]:
        title = web.clean(doc.get("title"), 120)
        if not title:
            continue
        author = web.clean(", ".join((doc.get("author_name") or [])[:2]), 80)
        year = doc.get("first_publish_year")
        cover = doc.get("cover_i")
        tiles.append({"title": title, "subtitle": " · ".join(x for x in (author, str(year or "")) if x),
                      "image": COVERS.format(int(cover)) if isinstance(cover, int) else "",
                      "say": f"Add the book {title}" + (f" by {author}" if author else "") + " to my reading list."})
    if not tiles:
        raise ValueError(f"Open Library found no books for {query}.")
    card = screen.card("webgallery", f"Books: {query}", "webview-books", data={"tiles": tiles},
                       text="Tap a book to add it to your reading list.")
    top = tiles[0]
    return screen.Shown(f"I found {len(tiles)} books on the screen; the top one is {top['title']}"
                        + (f" ({top['subtitle']})." if top["subtitle"] else "."), card)


async def link_preview(http: httpx.AsyncClient, url: str) -> screen.Shown:
    r = await web.get_public(http, url)
    url = str(r.url)
    markup = r.text[:web.MAX_PAGE]
    title_tag = re.search(r"<title[^>]*>(.*?)</title>", markup, re.S | re.I)
    title = web.clean(web.meta(markup, "og:title", "twitter:title") or (title_tag.group(1) if title_tag else ""), 150)
    description = web.clean(web.meta(markup, "og:description", "twitter:description", "description"), 500)
    image = web.meta(markup, "og:image", "twitter:image")
    image = web.https(urljoin(url, image)) if image else ""
    site = web.clean(web.meta(markup, "og:site_name"), 80) or (urlparse(url).hostname or "")
    card = screen.card("webcard", title or site, f"webview-link-{url}", data={
        "heading": title or site, "site": site, "text": description, "image": image, "link": url},
        buttons=[{"label": "Read it here", "say": read_say(url)},
                 {"label": "Save as a note", "say": f"Save the page {url} as a note in my Ideas folder."}])
    return screen.Shown(f"Here's a preview of {title or site} from {site}." + (f" {description}" if description else ""), card)


def image(settings: Settings, url: str, title: str, folder: str) -> screen.Shown:
    url = web.https(url)
    if not url:
        raise ValueError("I can only show pictures from https links.")
    folder = folder or "Ideas"
    memory.folder(settings, folder)  # a friendly error now rather than when the button is pressed
    card = screen.card("image", title or "Picture", f"webview-image-{url}", src=url,
                       buttons=[{"label": f"Save to {folder}", "say": f"Download {url} into my {folder} folder."}])
    return screen.Shown("The picture is on the screen.", card)


async def page_to_note(settings: Settings, http: httpx.AsyncClient, url: str, folder: str) -> screen.Shown:
    shown = await screen.read_page(http, url)
    page = shown.card
    title = web.clean(page.get("title"), 50).strip(" .") or "Web page"
    body = f"# {page.get('title')}\n\nFrom {page.get('url')}\n\n{page.get('text')}\n"
    name = memory.safe_name(title, "note title") + ".md"
    path = memory.save_file(settings, folder or "Ideas", name, body.encode("utf-8"))
    return screen.Shown(f"Saved {title} as {path.name} in {path.parent.name}; it's on the screen.",
                        screen.file_card(settings, path))


async def pet(http: httpx.AsyncClient, animal: str, breed: str) -> screen.Shown:
    if animal == "cat":
        body = await web.get_json(http, CAT, "cat picture")
        src = web.https((body[0] if isinstance(body, list) and body else {}).get("url"))
        again = "Show me another cat picture."
    else:
        breed = re.sub(r"[^a-z]+", "/", (breed or "").lower().strip()).strip("/")
        path = f"/breed/{breed}/images/random" if breed else "/breeds/image/random"
        body = await web.get_json(http, DOG + path, "dog picture", missing=f"The dog picture site doesn't know {breed}.")
        src = web.https(body.get("message") if isinstance(body, dict) else "")
        again = f"Show me another {breed.replace('/', ' ')} dog picture." if breed else "Show me another dog picture."
    if not src:
        raise ValueError(f"The {animal} picture site sent nothing I can show.")
    card = screen.card("image", f"A {animal}", f"webview-{animal}", src=src,
                       buttons=[{"label": "Another one", "say": again}])
    return screen.Shown(f"Here's a {animal} on the screen.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_on_screen",
        "description": "Bring the web onto the Alfred screen as pop-up windows (never the browser). news: BBC "
                       "headlines for a section, tap one to read it; wikipedia: an article summary with picture and "
                       "a Read full article button; books: search Open Library, covers, tap to add to the reading "
                       "list; link_preview: title, description and picture of a link; image: show an https picture "
                       "with a Save button; page_to_note: save a web page's words as a Markdown note and show it; "
                       "dog or cat: a random dog (optional breed) or cat picture with Another one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "section": {"type": "string", "enum": list(feeds.SECTIONS), "description": "news: default top."},
                "query": {"type": "string", "description": "wikipedia topic, or books title/author/subject."},
                "url": {"type": "string", "description": "link_preview, image or page_to_note link."},
                "title": {"type": "string"},
                "folder": {"type": "string", "description": "image or page_to_note: memory folder, default Ideas."},
                "breed": {"type": "string", "description": "dog breed, e.g. 'labrador' or 'spaniel cocker'."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"web_on_screen"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    action = args.get("action")
    if action == "news":
        return await news(http, args.get("section") or "top")
    if action == "wikipedia":
        return await wikipedia(http, args.get("query") or args.get("title"))
    if action == "books":
        return await books(http, args.get("query"))
    if action == "link_preview":
        return await link_preview(http, args.get("url"))
    if action == "image":
        return image(settings, args.get("url"), args.get("title") or "", args.get("folder") or "")
    if action == "page_to_note":
        return await page_to_note(settings, http, args.get("url") or "", args.get("folder") or "")
    if action in ("dog", "cat"):
        return await pet(http, action, args.get("breed") or "")
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
