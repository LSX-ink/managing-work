"""Kinetic Web Designs client finder: find local businesses with no website or a weak one, and audit any website.

find: looks a town or city anywhere in the world up on OpenStreetMap (Nominatim; give the country too when the name
is ambiguous, e.g. "Lagos, Nigeria" or "Seoul"), lists independent businesses of a kind near it (Overpass API; big
chains with a brand tag are skipped), then audits the websites of the first few. The results are ranked best bet first:
no website or only a Facebook or Instagram page (a "website" that is a social page counts as none and isn't audited),
then a website that doesn't load, then the lowest audit score. They're kept in kinetic-prospects.json and written
up as a report in Kinetic Web Designs/Prospects. Each prospect keeps its country (from the map, or the one given), so
quotes and outreach can use the local currency, language and email rules (see kinetic_world).

audit: reads one public website with plain HTTP (no scripts run, nothing is sent) and scores it out of 100 on what a
small business owner would care about: the padlock, working on phones, speed, being found on Google, tap-to-call, a
way to get in touch, an out-of-date footer, share previews and very old tech. Each problem comes with a plain-words
reason to use in a pitch. The report goes in Kinetic Web Designs/Audits/<domain>.md.

With JARVIS_GOOGLE_PLACES_KEY set, find uses Google Places Text Search (New) instead: "<trade> in <town>", up to 3
pages (60 businesses), asking only for the fields it needs (the field mask sets the price), skipping chains and
businesses closed for good. JARVIS_PLACES_MAX_CALLS (default 100) caps the calls per run of Alfred so a search can't run
up a bill. The key only travels in the request header; it is never shown or logged. Without a key, or if Google turns
the search down, it uses OpenStreetMap.

Shopify stores: every audited site is also checked for Shopify (cdn.shopify.com and the Shopify.theme object, with
/products.json only as a backup). A Shopify store is a "Shopify store" lead with store checks of its own, because
Shopify's fast CDN makes the plain audit score them well: the theme (and whether it's one of Shopify's free ones,
like Dawn), a reviews app, the home page's weight, scripts from other sites, images with no set size, a Google
description and whether the store has any movement or personality (video, animation, scroll effects, a static banner,
default fonts). Among stores, a free theme with no movement ranks first, then no reviews, then a heavy page. Store
kinds (fashion, beauty shops, wigs, jewellery, home and gifts, food and drink, sports shops, pet shops, kids shops,
art shops) are searched as shop categories; "online shop", "shopify" or "boutique" searches all of them. With
JARVIS_PAGESPEED_KEY set, a store also gets Google PageSpeed Insights' mobile score (skipped silently without it;
the key only travels in a request header and is never shown or logged).

Every link is checked with memory.check_public (through design_extract.fetch), so a page can't steer Alfred into this
PC or the home network. OpenStreetMap is volunteer-made, so some businesses are missing or out of date.
"""

import asyncio
import json
import re
import time
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

import design_extract
import freelance_clients
import kinetic_store as st
import kinetic_world as world
import screen
from config import Settings

NAMES = {"web_client_finder"}
ACTIONS = ["find", "audit", "prospects", "prospect", "mark", "add_lead", "forget"]
STATUSES = ["new", "lead", "contacted", "client", "not interested"]
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = "https://overpass-api.de/api/interpreter"
PLACES = "https://places.googleapis.com/v1/places:searchText"
PLACES_FIELDS = ",".join(f"places.{f}" for f in (  # the fewest fields: the field mask sets the price of each call
    "id", "displayName", "formattedAddress", "websiteUri", "nationalPhoneNumber", "internationalPhoneNumber",
    "googleMapsUri", "businessStatus", "types", "rating", "userRatingCount")) + ",nextPageToken"
PLACES_PAGES = 3  # 20 a page: 60 businesses at most
PAGESPEED = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PLACES_WORDS = {"cafes": "cafes", "restaurants": "restaurants", "takeaways": "takeaways", "pubs": "pubs and bars",
                "hairdressers": "hairdressers and barbers", "beauty": "beauty salons", "trades": "tradesmen",
                "garages": "car garages", "shops": "independent shops", "fitness": "gyms", "health": "clinics",
                "cleaners": "dry cleaners", "hotels": "guest houses", "mixed": "independent local businesses",
                "stores": "independent shops and boutiques", "fashion": "independent clothing boutiques",
                "beauty shops": "beauty and skincare shops", "wigs": "wig and hair shops",
                "jewellery": "independent jewellers", "home and gifts": "gift and homeware shops",
                "food and drink": "independent food and drink shops", "sports shops": "sportswear and fitness shops",
                "pet shops": "independent pet shops", "kids shops": "independent toy and children's shops",
                "art shops": "art and craft shops"}
CHAINS = {"costa", "starbucks", "caffe nero", "caffè nero", "greggs", "pret a manger", "mcdonald's", "burger king",
          "kfc", "subway", "domino's", "pizza hut", "papa john's", "nando's", "wetherspoon", "toni & guy", "toni&guy",
          "rush hair", "supercuts", "great clips", "kwik fit", "halfords", "specsavers", "boots", "superdrug",
          "tesco", "sainsbury's", "asda", "morrisons", "aldi", "lidl", "co-op", "puregym", "the gym group",
          "anytime fitness", "premier inn", "travelodge", "holiday inn", "mydentist", "timpson", "max spielmann"}
places_used = {"calls": 0}  # Places calls made since Alfred started, against JARVIS_PLACES_MAX_CALLS
OSM_HEADERS = {"User-Agent": "Alfred-assistant/1.0 (personal assistant; Kinetic Web Designs client finder)"}
MAX_HTML = 3 * 1024 * 1024
SLOW_SECONDS = 3.0
HEAVY_BYTES = 1_500_000
DEFAULT_AUDITS = 10
MAX_AUDITS = 20
KINDS = {
    "cafes": [("amenity", "cafe")],
    "restaurants": [("amenity", "restaurant")],
    "takeaways": [("amenity", "fast_food")],
    "pubs": [("amenity", "pub"), ("amenity", "bar")],
    "hairdressers": [("shop", "hairdresser")],
    "beauty": [("shop", "beauty"), ("shop", "cosmetics"), ("shop", "tattoo")],
    "trades": [("craft", v) for v in ("plumber", "electrician", "builder", "carpenter", "roofer", "painter",
                                      "gardener", "hvac", "tiler", "plasterer", "glaziery")],
    "garages": [("shop", "car_repair"), ("shop", "tyres"), ("amenity", "car_wash")],
    "shops": [("shop", v) for v in ("florist", "bakery", "butcher", "gift", "clothes", "boutique", "deli", "jewelry",
                                    "furniture", "pet", "bicycle")],
    "fitness": [("leisure", "fitness_centre"), ("leisure", "sports_centre")],
    "health": [("amenity", "dentist"), ("healthcare", "physiotherapist"), ("healthcare", "chiropractor"),
               ("amenity", "veterinary")],
    "cleaners": [("shop", "dry_cleaning"), ("shop", "laundry")],
    "hotels": [("tourism", "guest_house"), ("tourism", "hotel"), ("tourism", "bed_and_breakfast")],
}
STORE_KINDS = {  # shop categories for store (Shopify) leads, any kind of store
    "fashion": [("shop", v) for v in ("clothes", "boutique", "shoes", "bag", "fashion_accessories")],
    "beauty shops": [("shop", v) for v in ("cosmetics", "perfumery", "hairdresser_supply")],
    "wigs": [("shop", "wigs"), ("shop", "hairdresser_supply")],
    "jewellery": [("shop", "jewelry"), ("shop", "watches")],
    "home and gifts": [("shop", v) for v in ("gift", "houseware", "interior_decoration", "furniture", "candles",
                                              "florist")],
    "food and drink": [("shop", v) for v in ("deli", "confectionery", "chocolate", "wine", "alcohol", "tea", "coffee",
                                              "cheese", "pastry")],
    "sports shops": [("shop", v) for v in ("sports", "outdoor", "nutrition_supplements")],
    "pet shops": [("shop", "pet")],
    "kids shops": [("shop", v) for v in ("toys", "baby_goods", "games")],
    "art shops": [("shop", v) for v in ("art", "craft", "frame", "stationery")],
}
KINDS.update(STORE_KINDS)
KINDS["stores"] = list(dict.fromkeys(p for pairs in STORE_KINDS.values() for p in pairs))  # every kind of store
STORE_WORDS = [  # (pattern, store kind), checked before KIND_WORDS so "beauty shops" isn't a salon search
    (r"\bwigs?\b|hair (?:shop|store|extension)|hair and beauty suppl", "wigs"),
    (r"beauty (?:shop|store|product|brand|suppl)|skin ?care|cosmetic|make-?up|perfume|fragrance", "beauty shops"),
    (r"jewel|watch(?:es)? (?:shop|store)", "jewellery"),
    (r"fashion|cloth|apparel|shoe|footwear|trainers|streetwear|lingerie|menswear|womenswear|accessor", "fashion"),
    (r"\bgifts?\b|homeware|home ?decor|interior|candle|furniture|lifestyle (?:shop|store)", "home and gifts"),
    (r"food (?:and|&) drink|food (?:shop|store)|\bdeli|wine|chocolat|sweet shop|confection|tea (?:shop|store)|cheese|"
     r"hamper|coffee (?:roaster|beans)|bottle shop", "food and drink"),
    (r"sports? (?:shop|store)|sportswear|activewear|gym ?wear|athleisure|supplement|fitness (?:shop|store|brand|cloth)",
     "sports shops"),
    (r"\bpets?\b", "pet shops"),
    (r"\btoys?\b|\bkids\b|children|\bbaby\b", "kids shops"),
    (r"\bart (?:shop|store|suppl)|galler(?:y|ies)|craft (?:shop|store|suppl)|stationer", "art shops"),
    (r"shopify|online (?:shop|store)|e-?commerce|\bstores?\b|boutique|retail", "stores"),
]
MIXED = ["cafes", "restaurants", "hairdressers", "beauty", "trades", "garages", "shops"]
KIND_WORDS = {"barber": "hairdressers", "hair": "hairdressers", "cafe": "cafes", "coffee": "cafes", "restaurant": "restaurants", "takeaway": "takeaways", "pub": "pubs",
              "salon": "hairdressers",
              "nail": "beauty", "tattoo": "beauty", "plumber": "trades", "electrician": "trades", "builder": "trades",
              "trade": "trades", "mechanic": "garages", "garage": "garages", "car": "garages", "shop": "shops",
              "florist": "shops", "bakery": "shops", "gym": "fitness", "dentist": "health", "physio": "health",
              "vet": "health", "clean": "cleaners", "hotel": "hotels", "b&b": "hotels", "guest": "hotels", "bar": "pubs"}
OLD_TECH = re.compile(r"<(?:marquee|blink|frameset|font\s)|\.swf\b|<applet\b|jquery[.-]1\.\d", re.I)
BUILDERS = {"wix": "Wix", "squarespace": "Squarespace", "godaddy": "GoDaddy site builder", "weebly": "Weebly",
            "wordpress": "WordPress", "shopify": "Shopify", "jimdo": "Jimdo", "webflow": "Webflow", "ionos": "IONOS",
            "site123": "SITE123", "yell": "Yell"}


# ---- auditing ----------------------------------------------------------------------

class AuditParser(HTMLParser):
    """The parts of a page a website audit looks at."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.description, self.viewport, self.generator = "", "", "", ""
        self.h1 = self.images = self.no_alt = self.forms = 0
        self.tel, self.mailto, self.contact_link, self.og, self.icon, self.booking = False, False, False, False, False, False
        self.schema, self.text, self.emails = [], [], []
        self._in = ""

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name == "description":
                self.description = a.get("content", "").strip()
            elif name == "viewport":
                self.viewport = a.get("content", "")
            elif name == "generator":
                self.generator = a.get("content", "")
            elif name in ("og:title", "og:image"):
                self.og = True
        elif tag == "link" and "icon" in a.get("rel", "").lower():
            self.icon = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "img":
            self.images += 1
            if not a.get("alt", "").strip():
                self.no_alt += 1
        elif tag == "form":
            self.forms += 1
        elif tag == "a":
            href = a.get("href", "").strip().lower()
            if href.startswith("tel:"):
                self.tel = True
            elif href.startswith("mailto:"):
                self.mailto = True
                self.emails.append(href[7:].split("?")[0])
            elif "contact" in href:
                self.contact_link = True
            if re.search(r"book|appointment|reserv|order", href):
                self.booking = True
        elif tag == "script" and "ld+json" in a.get("type", "").lower():
            self._in = "schema"
        elif tag in ("title", "script", "style"):
            self._in = tag

    def handle_endtag(self, tag):
        if tag in ("title", "script", "style"):
            self._in = ""

    def handle_data(self, data):
        if self._in == "title" and not self.title:
            self.title = re.sub(r"\s+", " ", data).strip()[:120]
        elif self._in == "schema":
            self.schema.append(data)
        elif not self._in and data.strip() and len(self.text) < 4000:
            self.text.append(data.strip())


def copyright_year(text: str) -> int | None:
    years = [int(y) for y in re.findall(r"(?:©|&copy;|\(c\)|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", text, re.I)]
    return max(years) if years else None


def builder(markup: str, generator: str) -> str:
    """The site builder or platform a page was made with, if it's obvious."""
    gen = generator.lower()
    for key, name in BUILDERS.items():
        if key in gen:
            return name
    head = markup[:300_000].lower()
    for hint, name in (("static.wixstatic.com", "Wix"), ("squarespace.com", "Squarespace"),
                       ("cdn.shopify.com", "Shopify"), ("img1.wsimg.com", "GoDaddy site builder"),
                       ("weebly.com", "Weebly"), ("jimdo", "Jimdo"), ("webflow", "Webflow"), ("wp-content", "WordPress")):
        if hint in head:
            return name
    return ""


# ---- Shopify stores ----------------------------------------------------------------

STORE_LEAD = "Shopify store"
FREE_THEMES = ("Dawn", "Refresh", "Sense", "Craft", "Crave", "Studio", "Taste", "Origin", "Ride", "Colorblock",
               "Spotlight", "Publisher", "Trade", "Horizon", "Atelier", "Dwell", "Fabric", "Heritage", "Pitch",
               "Ritual", "Savor", "Tinker", "Vessel", "Debut", "Brooklyn", "Simple", "Narrative", "Venture",
               "Boundless", "Supply", "Minimal", "Express")  # Shopify's own free themes, old and new
FREE_THEME = re.compile(r"\b(" + "|".join(FREE_THEMES) + r")\b", re.I)
REVIEW_APPS = [("Judge.me", ("judge.me", "jdgm")), ("Yotpo", ("yotpo",)), ("Loox", ("loox.io", "loox-")),
               ("Okendo", ("okendo",)), ("Stamped", ("stamped.io", "stamped-")),
               ("Shopify Product Reviews", ("spr-badge", "productreviews.shopifycdn.com", "shopify-product-reviews")),
               ("Reviews.io", ("reviews.io", "reviewsio")), ("Trustpilot", ("widget.trustpilot.com", "trustpilot-widget")),
               ("Junip", ("junip",)), ("Fera", ("fera.ai",)), ("Ali Reviews", ("alireviews",)), ("Rivyo", ("rivyo",)),
               ("Feefo", ("feefo",))]
SHOPIFY_HOSTS = ("shopify.com", "shopifycdn.com", "shopifysvc.com", "myshopify.com", "shopifycloud.com", "shop.app")
VIDEO = re.compile(r"<video\b|youtube(?:-nocookie)?\.com/embed|player\.vimeo\.com|\.mp4\b|\.webm\b", re.I)
ANIMATION = re.compile(r"@keyframes|animation(?:-name)?\s*:\s*(?!none)[\w-]|\blottie|\bgsap\b|greensock|animate__|"
                       r"animate\.css|<marquee|\bmarquee\b|splitting\.js|\.gif\b", re.I)
SCROLL_FX = re.compile(r"scroll-trigger|animations\.js|data-aos|\baos\.(?:js|css)|data-scroll|locomotive|scrollreveal|"
                       r"parallax|animate--|reveal-on-scroll", re.I)
AUTOPLAY = re.compile(r"slideshow[^>]{0,300}(?:data-)?autoplay(?:=\"?true)?|autoplay[^>]{0,80}slideshow", re.I)
BANNER = re.compile(r"image-banner|image_banner|class=\"[^\"]*\bbanner\b|hero__image|slideshow", re.I)
FONTS = re.compile(r"font-family\s*:\s*([^;}\"<]+)", re.I)
DEFAULT_FONTS = {"assistant", "helvetica", "helvetica neue", "arial", "sans-serif", "serif", "system-ui",
                 "-apple-system", "blinkmacsystemfont", "segoe ui", "roboto", "times new roman", "times", "monospace",
                 "inherit", "initial", "ui-sans-serif", "apple color emoji", "segoe ui emoji", "noto sans"}
STORE_HEAVY_BYTES = 500_000  # the home page's own code; Shopify's CDN hides it in the speed check
MANY_SCRIPTS = 8
UNSIZED_IMAGES = 3


class StoreParser(HTMLParser):
    """Script hosts, images without a set size and the Google description of a store's home page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hosts, self.unsized, self.description = set(), 0, ""

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script" and a.get("src"):
            host = st.domain(a["src"] if not a["src"].startswith("//") else "https:" + a["src"])
            if host and "." in host:
                self.hosts.add(host)
        elif tag == "img" and not (a.get("width") and a.get("height")):
            self.unsized += 1
        elif tag == "meta" and (a.get("name") or "").lower() == "description":
            self.description = a.get("content", "").strip()


def theme_of(markup: str) -> tuple[str, str]:
    """(theme name, schema name) from the page's Shopify.theme object, or ("", "")."""
    m = re.search(r"Shopify\.theme\s*=\s*(\{.*?\})\s*;", markup, re.S)
    if not m:
        return "", ""
    try:
        data = json.loads(m.group(1))
    except ValueError:
        data = {k: v for k, v in re.findall(r'"(name|schema_name)"\s*:\s*"((?:[^"\\]|\\.)*)"', m.group(1))}
    if not isinstance(data, dict):
        return "", ""
    return st.clean(data.get("name"), 80), st.clean(data.get("schema_name"), 80)


def own_host(host: str, site: str) -> bool:
    return bool(site) and (host == site or host.endswith("." + site) or site.endswith("." + host))


def shopify_check(html: str, headers: dict | None = None, url: str = "") -> dict:
    """Whether a page is a Shopify store, and the store checks that matter for a makeover pitch.
    Detection: cdn.shopify.com or the Shopify.theme object (or Shopify's own response headers). maybe is True when
    the page only mentions Shopify, so /products.json can be tried as a backup."""
    markup = str(html or "")
    low = markup.lower()
    head = {str(k).lower(): str(v).lower() for k, v in (headers or {}).items()}
    by_header = any(k in head for k in ("x-shopid", "x-shopify-stage", "x-shardid")) or \
        "shopify" in head.get("powered-by", "") or "shopify" in head.get("server", "")
    found = "cdn.shopify.com" in low or bool(re.search(r"shopify\.theme\s*=", low)) or by_header
    name, schema = theme_of(markup)
    base = next((m.group(1) for m in (FREE_THEME.search(x) for x in (schema, name) if x) if m), "")
    base = next((t for t in FREE_THEMES if t.lower() == base.lower()), base)
    p = StoreParser()
    try:
        p.feed(markup)
    except Exception:  # broken markup: whatever was read so far
        pass
    site = st.domain(url)
    third = sorted(h for h in p.hosts if not own_host(h, site) and not any(h == s or h.endswith("." + s)
                                                                            for s in SHOPIFY_HOSTS))
    reviews = next((app for app, marks in REVIEW_APPS if any(m in low for m in marks)), "")
    video = bool(VIDEO.search(markup))
    animation = bool(ANIMATION.search(markup))
    scroll = bool(SCROLL_FX.search(markup))
    autoplay = bool(AUTOPLAY.search(markup))
    fonts = {f.strip().strip("'\"").lower() for x in FONTS.findall(markup) for f in x.split(",")
             if f.strip() and "var(" not in f}
    size = len(markup.encode("utf-8", "ignore"))
    no_motion = not (video or animation or scroll or autoplay)
    return {"is_shopify": found, "maybe": not found and ("shopify" in low or "myshopify.com" in str(url).lower()),
            "via": "page" if found and not by_header else "headers" if found else "",
            "theme": name or schema, "schema": schema, "base_theme": base or schema or name,
            "free_theme": bool(base), "reviews": reviews, "page_kb": round(size / 1024),
            "heavy": size > STORE_HEAVY_BYTES, "third_party": len(third), "third_party_hosts": third[:20],
            "images_no_size": p.unsized, "meta_description": bool(p.description), "video": video,
            "animation": animation, "scroll_effects": scroll, "autoplay": autoplay,
            "static_banner": bool(BANNER.search(markup)) and not (video or autoplay),
            "default_fonts": not any(f not in DEFAULT_FONTS for f in fonts), "no_motion": no_motion,
            "pagespeed": None}


def store_problems(s: dict) -> list[dict]:
    """The store checks as audit problems, biggest first, with plain-words reasons."""
    out = []

    def hit(points, short, why):
        out.append({"points": points, "problem": short, "why": why, "store": True})

    if s.get("free_theme"):
        hit(12, f"Shopify's free {s['base_theme']} theme", "It looks like thousands of other Shopify stores, so "
                                                              "nothing says this is your brand.")
    if s.get("no_motion"):
        bits = ["no video, animation or scroll effects"] + (["a static banner"] if s.get("static_banner") else []) + \
            (["default fonts"] if s.get("default_fonts") else [])
        hit(10, "No movement or personality", "The home page has " + ", ".join(bits[:-1]) + (" and " if len(bits) > 1
            else "") + bits[-1] + ", so it feels flat next to the brands shoppers follow on Instagram and TikTok.")
    if not s.get("reviews"):
        hit(8, "No customer reviews on the store", "First-time shoppers have nothing to reassure them before they "
                                                   "buy, and reviews lift sales.")
    if isinstance(s.get("pagespeed"), int) and s["pagespeed"] < 50:
        hit(8, f"Slow on phones (Google PageSpeed {s['pagespeed']}/100)", "Google's own test says the store is slow "
                                                                          "on a phone, where most shoppers buy.")
    if s.get("heavy"):
        hit(6, f"Heavy home page ({s['page_kb']} KB of code)", "A big page is slow on phones, where most shoppers buy.")
    if s.get("third_party", 0) >= MANY_SCRIPTS:
        hit(4, f"{s['third_party']} add-on scripts from other sites", "Every extra app script slows the store down "
                                                                      "and can get in the way at checkout.")
    if s.get("images_no_size", 0) >= UNSIZED_IMAGES:
        hit(3, "Images jump as the page loads", "Pictures without a set size make the page shift while it loads, "
                                               "which annoys shoppers and Google counts against it.")
    return out


def apply_store(result: dict, store: dict) -> dict:
    """Mark an audit as a Shopify store lead: its store checks join the problems and the score."""
    result["problems"] = [x for x in result.get("problems", []) if not x.get("store")] + store_problems(store)
    result["problems"].sort(key=lambda x: -x["points"])
    result["score"] = max(0, 100 - sum(x["points"] for x in result["problems"]))
    result["grade"] = grade(result["score"])
    result.update({"shopify": store, "builder": "Shopify", "lead_type": STORE_LEAD})
    return result


async def products_json(http: httpx.AsyncClient, url: str) -> bool:
    """The backup signal: a Shopify store answers /products.json with its product list."""
    parts = urlparse(url)
    try:
        _, kind, text = await design_extract.fetch(http, f"{parts.scheme}://{parts.netloc}/products.json?limit=1",
                                                   512 * 1024)
        data = json.loads(text)
    except (ValueError, design_extract.TooBig):
        return False
    return isinstance(data, dict) and isinstance(data.get("products"), list)


async def pagespeed(settings: Settings, http: httpx.AsyncClient, url: str) -> int | None:
    """Google PageSpeed Insights' mobile performance score (0 to 100), or None without a key or on any trouble.
    The key goes only in the X-Goog-Api-Key header, never in the address, and is never shown or logged."""
    key = getattr(settings, "pagespeed_key", "")
    if not key:
        return None
    try:
        r = await http.get(PAGESPEED, params={"url": url, "strategy": "mobile", "category": "performance"},
                           headers={"X-Goog-Api-Key": key}, timeout=90)
        if r.status_code != 200:
            return None
        score = r.json()["lighthouseResult"]["categories"]["performance"]["score"]
        return int(round(float(score) * 100))
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None


async def with_pagespeed(settings: Settings, http: httpx.AsyncClient, result: dict) -> dict:
    """Add the PageSpeed mobile score to a Shopify store's audit when JARVIS_PAGESPEED_KEY is set."""
    store = result.get("shopify")
    if store and store.get("is_shopify"):
        score = await pagespeed(settings, http, result["url"])
        if score is not None:
            store["pagespeed"] = score
            apply_store(result, store)
    return result


def is_store(p: dict) -> bool:
    """A Shopify store lead: its website's audit found Shopify."""
    return bool(((p.get("audit") or {}).get("shopify") or {}).get("is_shopify"))


def store_tier(s: dict) -> int:
    """Among stores, best bet first: a free theme with no movement, then no reviews, then a heavy (or slow) page,
    then a free theme or no movement on its own."""
    slow = s.get("heavy") or (isinstance(s.get("pagespeed"), int) and s["pagespeed"] < 50)
    return (0 if s.get("free_theme") and s.get("no_motion") else 8) + (0 if not s.get("reviews") else 4) + \
        (0 if slow else 2) + (0 if s.get("free_theme") or s.get("no_motion") else 1)


def score_page(url: str, markup: str, seconds: float, size: int, https_ok: bool, this_year: int) -> dict:
    """Score a fetched page out of 100, with each problem in plain words."""
    p = AuditParser()
    p.feed(markup)
    text = " ".join(p.text)
    problems = []

    def hit(points, short, why):
        problems.append({"points": points, "problem": short, "why": why})

    if not https_ok:
        hit(20, "No padlock (no HTTPS)", "Browsers label the site 'Not secure', which puts customers off and hurts "
                                         "its Google ranking.")
    if "width=device-width" not in p.viewport.replace(" ", "").lower():
        hit(20, "Not made for phones", "Most visitors are on a phone, and the page shows as a tiny desktop page they "
                                       "have to pinch and zoom.")
    if seconds > SLOW_SECONDS:
        hit(10, f"Slow to load ({seconds:.1f}s)", "Over half of phone visitors leave a page that takes longer than "
                                                   "3 seconds.")
    if size > HEAVY_BYTES:
        hit(5, "Heavy page", "The page is big before images even load, which eats data and slows phones down.")
    if len(p.title) < 10 or p.title.lower() in ("home", "homepage", "welcome", "index"):
        hit(8, "Weak page title", "The title is what shows in Google results; a vague one means fewer clicks.")
    if not p.description:
        hit(7, "No Google description", "Google makes up its own snippet, so the listing doesn't sell the business.")
    if not p.h1:
        hit(5, "No main heading", "There is no clear headline telling visitors (and Google) what the business does.")
    if not p.tel:
        hit(6, "Phone number isn't tap-to-call", "On a phone, customers can't just tap to ring.")
    if not (p.forms or p.mailto or p.contact_link):
        hit(8, "No easy way to get in touch", "There's no contact form, email link or contact page on the home page.")
    year = copyright_year(text)
    if year and year <= this_year - 2:
        hit(8, f"Footer says © {year}", "It makes the business look closed or neglected.")
    if p.images >= 3 and p.no_alt * 2 > p.images:
        hit(5, "Images have no descriptions", "Screen readers and Google can't tell what the pictures show.")
    if not p.og:
        hit(4, "No share preview", "Links shared on WhatsApp or Facebook show no picture or title.")
    if not any(re.search(r"LocalBusiness|Restaurant|Store|\"@type\"\s*:\s*\"\w*(Business|Service)", s) for s in p.schema):
        hit(4, "Google can't read the business details", "No structured data, so opening hours and address are less "
                                                         "likely to show in search.")
    if OLD_TECH.search(markup):
        hit(10, "Built with very old tech", "Parts of the page use code from the 2000s that modern browsers and "
                                            "phones handle badly.")
    if not p.icon:
        hit(3, "No tab icon", "The browser tab shows a blank icon instead of the logo.")
    score = max(0, 100 - sum(x["points"] for x in problems))
    problems.sort(key=lambda x: -x["points"])
    return {"url": url, "title": p.title, "score": score, "grade": grade(score), "problems": problems,
            "seconds": round(seconds, 1), "builder": builder(markup, p.generator), "booking": p.booking,
            "emails": list(dict.fromkeys(e for e in p.emails if "@" in e))[:3], "copyright": year,
            "date": st.today().isoformat()}


def grade(score: int) -> str:
    return "weak" if score < 50 else "needs work" if score < 75 else "good"


def down(url: str, reason: str) -> dict:
    return {"url": url, "title": "", "score": 0, "grade": "down", "seconds": 0, "builder": "", "booking": False,
            "emails": [], "copyright": None, "date": st.today().isoformat(),
            "problems": [{"points": 100, "problem": "Website doesn't load", "why": reason}]}


async def audit_url(http: httpx.AsyncClient, url: str) -> dict:
    """Fetch a site (https first, then http) and score it."""
    url = design_extract.check_url(url)
    https_url = re.sub(r"^http://", "https://", url, flags=re.I)
    tries = [https_url, "http://" + https_url[8:]]
    last = "It didn't answer."
    for attempt in tries:
        start = time.monotonic()
        headers = {}
        try:
            final, kind, markup = await design_extract.fetch(http, attempt, MAX_HTML, headers)
        except design_extract.TooBig:
            last = "The home page is too big to load sensibly."
            continue
        except ValueError as e:
            if "this PC or your home network" in str(e):
                raise
            last = str(e) + " It may only block robots, so open it yourself before you pitch."
            continue
        if kind and "html" not in kind:
            return down(final, "The address doesn't open a web page.")
        seconds = time.monotonic() - start
        result = score_page(final, markup, seconds, len(markup.encode("utf-8", "ignore")),
                            urlparse(final).scheme == "https", st.today().year)
        store = shopify_check(markup, headers, final)
        if store["maybe"] and await products_json(http, final):  # only a backup signal
            store.update({"is_shopify": True, "via": "products.json"})
        return apply_store(result, store) if store["is_shopify"] else result
    return down(https_url, last)


def audit_md(name: str, a: dict) -> str:
    lines = [f"# Website audit: {name}", "", f"{a['url']} checked by Alfred on {a['date']}.", "",
             f"**Score: {a['score']}/100 ({a['grade']})**", ""]
    if a.get("builder"):
        lines += [f"Built with: {a['builder']}", ""]
    s = a.get("shopify")
    if s:
        lines += ["## Shopify store checks", "",
                  f"- Theme: {s['theme'] or 'not named'}" + (" (one of Shopify's free themes)" if s["free_theme"] else ""),
                  f"- Reviews app: {s['reviews'] or 'none found'}",
                  f"- Movement: {'none found (no video, animation or scroll effects)' if s['no_motion'] else 'some'}"
                  + ("; static banner" if s["static_banner"] else "") + ("; default fonts" if s["default_fonts"] else ""),
                  f"- Home page code: {s['page_kb']} KB; scripts from {s['third_party']} other sites; "
                  f"{s['images_no_size']} images with no set size; Google description: "
                  f"{'yes' if s['meta_description'] else 'no'}"]
        if s.get("pagespeed") is not None:
            lines.append(f"- Google PageSpeed on phones: {s['pagespeed']}/100")
        lines.append("")
    lines += ["## What to fix, biggest first", ""]
    lines += [f"- **{x['problem']}** (-{x['points']}). {x['why']}" for x in a["problems"]] or ["- Nothing big. A strong site."]
    lines += ["", "## How to use this", "",
              "Lead with the top two or three problems in plain words and offer a free mock-up of a new home page.",
              "Scores come from the page's code only, so check the site yourself on a phone before you pitch.", ""]
    return "\n".join(lines)


# ---- finding businesses ------------------------------------------------------------

def kind_key(kind) -> str:
    k = str(kind or "").strip().lower()
    if not k or k in ("any", "all", "mixed", "businesses", "small businesses", "local businesses"):
        return "mixed"
    if k in KINDS:
        return k
    for pattern, key in STORE_WORDS:
        if re.search(pattern, k):
            return key
    for word, key in KIND_WORDS.items():
        if word in k:
            return key
    raise ValueError("Which kind of business? " + ", ".join(KINDS) + ", or mixed.")


def overpass_query(lat: float, lon: float, radius: int, kind: str) -> str:
    pairs = [p for k in (MIXED if kind == "mixed" else [kind]) for p in KINDS[k]]
    parts = "".join(f'nwr["{k}"="{v}"]["name"](around:{radius},{lat},{lon});' for k, v in pairs)
    return f"[out:json][timeout:25];({parts});out center tags 300;"


def kind_label(tags: dict) -> str:
    for key in ("shop", "craft", "amenity", "leisure", "healthcare", "tourism"):
        if tags.get(key):
            return tags[key].replace("_", " ")
    return "business"


SOCIAL = {"facebook": ("facebook.com", "fb.com", "fb.me"), "instagram": ("instagram.com", "instagr.am")}


def social_of(url: str) -> str:
    """"facebook" or "instagram" when a web address is only a social media page, else ""."""
    host = st.domain(url)
    return next((k for k, hosts in SOCIAL.items() if any(host == h or host.endswith("." + h) for h in hosts)), "")


def split_social(b: dict) -> dict:
    """A "website" that is really a Facebook or Instagram page is kept as that page, and the business has no website."""
    kind = social_of(b.get("website", ""))
    if kind:
        b[kind] = b.get(kind) or b["website"]
        b["website"] = ""
    return b


def social_only(p: dict) -> str:
    """"Facebook" or "Instagram" for a business with no website but a social page, else ""."""
    if p.get("website") and not social_of(p["website"]):
        return ""
    return "Facebook" if p.get("facebook") or social_of(p.get("website", "")) == "facebook" else \
        "Instagram" if p.get("instagram") or social_of(p.get("website", "")) == "instagram" else ""


def business_of(element: dict, town: str, country: str = "") -> dict | None:
    tags = element.get("tags") or {}
    name = st.clean(tags.get("name"), 80)
    if not name or tags.get("brand") or tags.get("brand:wikidata") or tags.get("disused") == "yes":
        return None  # chains have a brand tag and hire agencies, not local designers
    website = tags.get("website") or tags.get("contact:website") or tags.get("url") or ""
    address = ", ".join(x for x in (" ".join(filter(None, (tags.get("addr:housenumber"), tags.get("addr:street")))),
                                    tags.get("addr:city"), tags.get("addr:postcode")) if x)
    where_ = element.get("center") if isinstance(element.get("center"), dict) else element  # ways have a centre
    try:
        lat, lon = round(float(where_["lat"]), 6), round(float(where_["lon"]), 6)
    except (KeyError, TypeError, ValueError):
        lat = lon = None
    return split_social({
        "name": name, "kind": kind_label(tags), "town": town, "country": country, "website": st.clean(website, 200),
        "phone": st.clean(tags.get("phone") or tags.get("contact:phone"), 40),
        "email": st.clean(tags.get("email") or tags.get("contact:email"), 80), "address": st.clean(address, 160),
        "facebook": st.clean(tags.get("contact:facebook") or tags.get("facebook"), 200),
        "instagram": st.clean(tags.get("contact:instagram") or tags.get("instagram"), 200),
        "osm": f"{element.get('type', '')}/{element.get('id', '')}", "lat": lat, "lon": lon})


async def geocode(http: httpx.AsyncClient, place: str) -> tuple[float, float, str, str]:
    """(latitude, longitude, town name, two-letter country code or "") for a place anywhere in the world."""
    try:
        r = await http.get(NOMINATIM, params={"q": place, "format": "jsonv2", "limit": 1, "addressdetails": 1},
                           headers={**OSM_HEADERS, "Accept-Language": "en"}, timeout=15)
        r.raise_for_status()
        found = r.json()
    except (httpx.HTTPError, ValueError):
        raise ValueError("I couldn't look that place up on the map right now; try again in a minute.") from None
    if not found:
        raise ValueError(f"I couldn't find {place} on the map. Try adding the country, e.g. 'Lagos, Nigeria', or a "
                         "postcode.")
    hit = found[0]
    code = str((hit.get("address") or {}).get("country_code") or "").upper()
    return (float(hit["lat"]), float(hit["lon"]), st.clean(hit.get("display_name", place).split(",")[0], 60),
            code if re.fullmatch(r"[A-Z]{2}", code) else "")


async def nearby(http: httpx.AsyncClient, lat: float, lon: float, radius: int, kind: str, town: str,
                 country: str = "") -> list[dict]:
    try:
        r = await http.post(OVERPASS, data={"data": overpass_query(lat, lon, radius, kind)}, headers=OSM_HEADERS,
                            timeout=40)
        r.raise_for_status()
        elements = r.json().get("elements", [])
    except (httpx.HTTPError, ValueError):
        raise ValueError("The OpenStreetMap business search is busy; try again in a minute.") from None
    out, seen = [], set()
    for e in elements:
        b = business_of(e, town, country)
        if b and (key := (b["name"].lower(), b["address"].lower())) not in seen:
            seen.add(key)
            out.append(b)
    return out


def chain_name(name: str) -> bool:
    key = name.lower().replace("’", "'")
    return any(key == c or key.startswith(c + " ") for c in CHAINS)


def business_of_place(place: dict, town: str, country: str = "") -> dict | None:
    """A Google Places result as a prospect, or None for a chain or a business that has closed for good."""
    name = st.clean((place.get("displayName") or {}).get("text"), 80)
    if not name or chain_name(name) or place.get("businessStatus") == "CLOSED_PERMANENTLY":
        return None
    address = st.clean(place.get("formattedAddress"), 160)
    country = country or (world.country_code(address.rsplit(",", 1)[-1]) if address else "")
    kind = next((t.replace("_", " ") for t in place.get("types") or []
                 if t not in ("point_of_interest", "establishment", "store", "food")), "business")
    return split_social({
        "name": name, "kind": kind, "town": town, "country": country, "website": st.clean(place.get("websiteUri"), 200),
        "phone": st.clean(place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber"), 40),
        "email": "", "address": address, "facebook": "", "instagram": "", "osm": "",
        "google": st.clean(place.get("id"), 120), "maps": st.clean(place.get("googleMapsUri"), 200),
        "rating": place.get("rating") if isinstance(place.get("rating"), (int, float)) else None,
        "reviews": place.get("userRatingCount") if isinstance(place.get("userRatingCount"), int) else None})


async def places_search(settings: Settings, http: httpx.AsyncClient, kind: str, place: str, town: str,
                        country: str = "") -> list[dict]:
    """Up to 60 independent businesses from Google Places Text Search (New): "<trade> in <place>", 3 pages at most.
    The key goes only in the X-Goog-Api-Key header and is never shown or logged."""
    headers = {"X-Goog-Api-Key": settings.google_places_key, "X-Goog-FieldMask": PLACES_FIELDS,
               "Content-Type": "application/json"}
    query = f"{PLACES_WORDS[kind]} in {place}"
    places, token = [], ""
    for _ in range(PLACES_PAGES):
        if places_used["calls"] >= settings.places_max_calls:
            if places:
                break
            raise ValueError(f"I've made {places_used['calls']} Google Places searches since I started, which is the "
                             "limit in JARVIS_PLACES_MAX_CALLS, so I've stopped to keep the bill down. Restart me or "
                             "raise the limit to search again.")
        places_used["calls"] += 1
        body = {"textQuery": query, "pageSize": 20, **({"pageToken": token} if token else {})}
        try:
            r = await http.post(PLACES, json=body, headers=headers, timeout=20)
        except httpx.HTTPError:
            raise ValueError("Google Places didn't answer just now.") from None
        if r.status_code in (400, 401, 403):
            raise ValueError("Google Places turned the key down. Check JARVIS_GOOGLE_PLACES_KEY and that "
                             "\"Places API (New)\" is enabled for it.")
        if r.status_code != 200:
            raise ValueError("Google Places is busy; try again in a minute.")
        try:
            data = r.json()
        except ValueError:
            raise ValueError("Google Places sent back something I couldn't read.") from None
        places += [x for x in data.get("places") or [] if isinstance(x, dict)]
        token = str(data.get("nextPageToken") or "")
        if not token:
            break
    names = [st.clean((x.get("displayName") or {}).get("text"), 80).lower() for x in places]
    out, seen = [], set()
    for x, key in zip(places, names):
        b = business_of_place(x, town, country)
        if b and names.count(key) < 3 and b["google"] not in seen:  # three or more branches here: a chain
            seen.add(b["google"])
            out.append(b)
    return out


UNCHECKED = 5  # rank group of a website not checked yet: last


def rank_key(p: dict):
    """Best bets first: no website or only a Facebook/Instagram page (ones you can reach first), then a broken site,
    then a weak site (under 50), then Shopify stores (a free theme with no movement first, then no reviews, then a
    heavy page), then the rest by audit score; websites not checked yet go last."""
    a = p.get("audit")
    if not p.get("website") or social_only(p):
        return (0, 0 if p.get("phone") or p.get("email") else 1, 0, p["name"])
    if not a:
        return (UNCHECKED, 0, 0, p["name"])
    if a["grade"] == "down":
        return (1, 0, 0, p["name"])
    if a.get("score", 0) < 50:
        return (2, 0, a["score"], p["name"])
    if is_store(p):
        return (3, store_tier(a["shopify"]), a["score"], p["name"])
    return (4, 0, a["score"], p["name"])


def kind_text(p: dict) -> str:
    """The prospect's kind, with "Shopify store" when it is one."""
    return f"{p.get('kind') or 'business'}, {STORE_LEAD}" if is_store(p) else p.get("kind") or "business"


def headline(p: dict) -> tuple[str, str]:
    """(score text, top problem) for a prospect."""
    if not p.get("website") or social_only(p):
        only = social_only(p)
        return "no site", "No website" + (f" ({only} only)" if only else "")
    a = p.get("audit")
    if not a:
        return "not checked", "-"
    if a["grade"] == "down":
        return "down", "Website doesn't load"
    return f"{a['score']}/100", a["problems"][0]["problem"] if a["problems"] else "Strong site"


BOOKABLE = ("hair", "barber", "beauty", "nail", "salon", "spa", "massage", "tattoo", "lash", "brow", "dentist",
            "physio", "chiro", "clinic", "gym", "fitness", "restaurant", "vet", "groom")  # trades people book
PLAIN = [  # (audit problem starts with, plain words for a first line, the same for a short DM, a short label),
    # most persuasive first
    ("Not made for phones", "is hard to use on a phone: it shows as a tiny desktop page, and most of your "
                            "customers are on their phones", "is hard to use on a phone, where most of your "
                                                             "customers are", "broken on phones"),
    ("No online booking", "has no way to book online, so people who want to book in the evening go elsewhere",
     "has no online booking, so evening bookers go elsewhere", "no online booking"),
    ("No padlock", "shows as \"Not secure\" in browsers, which puts customers off and pushes you down Google",
     "shows as \"Not secure\" in browsers, which puts customers off", "\"Not secure\" warning"),
    ("Slow to load", "is slow to load on a phone, and over half of phone visitors give up after 3 seconds",
     "is slow on phones, and most people give up after 3 seconds", "slow on phones"),
    ("No easy way to get in touch", "has no easy way to get in touch: no contact form, email link or contact page",
     "has no easy way to get in touch", "no way to get in touch"),
    ("Phone number isn't tap-to-call", "doesn't let customers tap to ring you from their phone",
     "doesn't let customers tap to ring you", "no tap-to-call"),
    ("Footer says", "says © {year} at the bottom, which makes the business look closed",
     "says © {year} at the bottom, which looks closed", "out-of-date footer"),
    ("Built with very old tech", "is built with very old code that phones handle badly",
     "is built with old code that phones handle badly", "very old tech"),
]


def bookable(p: dict) -> bool:
    text = f"{p.get('kind', '')} {p.get('name', '')}".lower()
    return any(word in text for word in BOOKABLE)


def store_problem(p: dict, name: str, site: str) -> dict:
    """A Shopify store's biggest problem in plain words: a free theme or no movement first, then no reviews, then
    speed. Empty when none of them stands out."""
    s = (p.get("audit") or {}).get("shopify") or {}
    if s.get("free_theme"):
        base = s.get("base_theme") or "default"
        which = "Shopify's free default theme" if base.lower() == "dawn" else f"Shopify's free {base} theme"
        tail = f"no movement, nothing that feels like {name}" if s.get("no_motion") else f"nothing that feels like {name}"
        line = f"Your store uses {which}, so it looks like thousands of others: {tail}."
        return {"key": "shopify_theme", "label": f"free {base} theme" + (", no movement" if s.get("no_motion") else ""),
                "line": line, "short": line}
    if s.get("no_motion"):
        line = (f"Your store ({site}) has no movement and no personality: no video, no animation, nothing that feels "
                f"like {name}.")
        return {"key": "shopify_motion", "label": "no movement or personality", "line": line, "short": line}
    if not s.get("reviews"):
        return {"key": "shopify_reviews", "label": "no reviews on the store",
                "line": f"Your store ({site}) shows no customer reviews, so first-time shoppers have nothing to "
                        "reassure them before they buy.",
                "short": f"Your store ({site}) shows no customer reviews, so new shoppers have nothing to go on."}
    if isinstance(s.get("pagespeed"), int) and s["pagespeed"] < 50:
        line = (f"Your store ({site}) is slow on phones: Google gives it {s['pagespeed']} out of 100, and most "
                "shoppers buy on their phone.")
        return {"key": "shopify_speed", "label": "slow on phones", "line": line, "short": line}
    if s.get("heavy"):
        line = f"Your store ({site}) has a heavy home page that's slow on phones, where most shoppers buy."
        return {"key": "shopify_heavy", "label": "heavy home page", "line": line, "short": line}
    return {}


def biggest_problem(p: dict) -> dict:
    """The lead's single biggest problem in plain words, for the first line of a first message:
    {"key", "label" (a few words), "line" (a sentence to them), "short" (the same for a DM)}. Empty when nothing
    stands out."""
    name = p.get("name") or "your business"
    only = social_only(p)
    if not p.get("website") or only:
        if only:
            return {"key": "social", "label": f"{only} only, no website",
                    "line": f"I couldn't find a website for {name}, only your {only} page, so people searching on "
                            "Google are finding someone else first.",
                    "short": f"I couldn't find a website for {name}, only your {only} page, so Google searchers "
                             "find someone else first."}
        return {"key": "none", "label": "no website",
                "line": f"I searched for {name} online and couldn't find a website, only a map listing, so people "
                        "searching on Google are finding someone else first.",
                "short": f"I couldn't find a website for {name}, so people searching on Google find someone else "
                         "first."}
    site = st.domain(p["website"]) or p["website"]
    a = p.get("audit") or {}
    if a.get("grade") == "down":
        return {"key": "down", "label": "website won't load",
                "line": f"I tried your website ({site}) and it won't load, so customers may be giving up and going "
                        "elsewhere.",
                "short": f"Your website ({site}) won't load, so customers may be giving up."}
    if is_store(p) and (found := store_problem(p, name, site)):
        return found
    names = [x.get("problem", "") for x in a.get("problems") or []]
    if a and bookable(p) and not a.get("booking"):
        names.append("No online booking")
    for start, words, brief, label in PLAIN:
        hit = next((n for n in names if n.startswith(start)), "")
        if hit:
            year = (re.search(r"\d{4}", hit) or [""])[0]
            return {"key": start, "label": label.replace("{year}", year),
                    "line": f"Your website ({site}) {words.replace('{year}', year)}.",
                    "short": f"Your website ({site}) {brief.replace('{year}', year)}."}
    if names:
        top = (a.get("problems") or [{}])[0]
        line = f"I had a look at your website ({site}): {names[0][0].lower() + names[0][1:]}."
        return {"key": "other", "label": names[0].lower(), "line": f"{line} {top.get('why', '')}".strip(),
                "short": line}
    return {}


def merge(settings: Settings, found: list[dict]) -> list[dict]:
    """Add or refresh prospects in kinetic-prospects.json; returns the stored rows for found."""
    rows = st.rows_of(settings, st.PROSPECTS)
    out = []
    for b in found:
        hit = next((r for r in rows if b.get("osm") and r.get("osm") == b["osm"]), None) or \
            next((r for r in rows if b.get("google") and r.get("google") == b["google"]), None) or \
            next((r for r in rows if r["name"].lower() == b["name"].lower() and
                  (r.get("address", "").lower() == b.get("address", "").lower() or
                   st.domain(r.get("website")) == st.domain(b.get("website")) != "")), None)
        if hit:
            hit.update({k: v for k, v in b.items() if v})
            if b.get("website") == "" and social_of(hit.get("website", "")):
                split_social(hit)  # saved before social pages counted as no website
        else:
            if len(rows) >= st.MAX_ROWS:
                break
            hit = {"id": st.next_id(rows), "status": "new", "found": st.today().isoformat(), **b}
            rows.append(hit)
        out.append(hit)
    st.save(settings, st.PROSPECTS, rows)
    return out


def report_md(town: str, kind: str, rows: list[dict], country: str = "", source: str = "OpenStreetMap") -> str:
    where_ = f"{town}, {world.country_name(country)}" if country else town
    lines = [f"# Web design prospects: {kind} near {where_}", "", f"Found by Alfred on {st.today().isoformat()} from "
             f"{source}. Best bets first. Check each business is still trading before you contact them.", "",
             "| # | Business | Type | Website | Score | Biggest problem | Phone | Address |",
             "|---|---|---|---|---|---|---|---|"]
    for p in rows:
        score, problem = headline(p)
        cells = [str(p["id"]), p["name"], kind_text(p), p.get("website") or "none", score, problem, p.get("phone") or "-",
                 p.get("address") or "-"]
        lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    lines += ["", "Say \"audit <business>\" for the full report, \"write outreach for <business>\" for a first "
              "message, or \"mock up a home page for <business>\" for a free sample to win them over.", ""]
    return "\n".join(lines)


def prospect_rows(rows: list[dict]) -> list[list[str]]:
    out = []
    for p in rows:
        score, problem = headline(p)
        out.append([str(p["id"]), p["name"], kind_text(p), st.domain(p.get("website")) or "none", score, problem,
                    p.get("status", "new")])
    return out


COLUMNS = ["#", "Business", "Type", "Website", "Score", "Biggest problem", "Status"]


async def find(settings: Settings, args: dict, http: httpx.AsyncClient) -> screen.Shown:
    place = st.need(args.get("town"), "town, city or postcode", 80)
    asked = st.clean(args.get("country"), 60)
    if asked and asked.lower() not in place.lower():
        place = f"{place}, {asked}"
    week = st.trade_of_week(settings)
    kind = kind_key(args.get("kind") or week.get("kind"))  # no trade given: the trade of the week
    weekly = f" (this week's trade, {week['label']})" if week and not args.get("kind") else ""
    radius = int(min(max(st.number(args.get("radius_km") or 3, "distance"), 0.5), 15) * 1000)
    found, source, fell_back = [], "OpenStreetMap", ""
    if settings.google_places_key:
        town = st.clean(place.split(",")[0], 60) or place
        try:
            found = await places_search(settings, http, kind, place, town, world.country_code(asked))
            source = "Google Maps"
        except ValueError as e:
            fell_back = f" {e} I used OpenStreetMap instead."
    if source == "OpenStreetMap":
        lat, lon, town, country = await geocode(http, place)
        country = country or world.country_code(asked)  # the map's answer first; it knows "Lagos" is in Nigeria
        found = await nearby(http, lat, lon, radius, kind, town, country)
    if not found:
        raise ValueError(f"{source} has no independent {kind} listed " +
                         (f"within {radius // 1000} km of {town}" if source == "OpenStreetMap" else f"in {town}") +
                         ". Try a bigger distance or another kind of business." + fell_back)
    country = next((b["country"] for b in found if b.get("country")), "")
    limit = int(min(max(int(args.get("audit_limit") or DEFAULT_AUDITS), 0), MAX_AUDITS))
    to_check = [b for b in found if b["website"]][:limit]
    gate = asyncio.Semaphore(4)

    async def check(b):
        async with gate:
            try:
                b["audit"] = await with_pagespeed(settings, http, await audit_url(http, b["website"]))
            except ValueError as e:
                b["audit"] = down(b["website"], str(e))
            if is_store(b):
                b["lead_type"] = STORE_LEAD

    await asyncio.gather(*(check(b) for b in to_check))
    rows = sorted(merge(settings, found), key=rank_key)
    label = "businesses" if kind == "mixed" else kind
    path = st.write(settings, ("Prospects",), f"{town} {label} {st.today().isoformat()}.md",
                    report_md(town, label, rows, country, source), replace=True)
    none = sum(1 for p in rows if not p.get("website"))
    weak = sum(1 for p in rows if p.get("audit") and p["audit"]["grade"] in ("weak", "down"))
    unchecked = sum(1 for p in rows if p.get("website") and not p.get("audit"))
    best = [f"{p['name']} ({headline(p)[1].lower()})" for p in rows[:3]]
    text = (f"I found {len(rows)} independent {label}{weekly} near {town}: {none} with no website and {weak} with a weak or "
            f"broken one. Best bets: {', '.join(best)}.")
    stores = sum(1 for p in rows if is_store(p))
    if stores:
        text += (f" {stores} run on Shopify: store makeover leads, ranked by a free theme with no movement, then no "
                 "reviews, then a heavy page.")
    if unchecked:
        text += f" I didn't check {unchecked} other website{'s' if unchecked != 1 else ''}; ask me to audit any of them."
    text += f" The list is saved in {st.where(settings, path)}." + (" Found on Google Maps." if source != "OpenStreetMap" else "") + fell_back
    top = rows[0]
    return st.table(text, f"Prospects near {town}", COLUMNS, prospect_rows(rows[:60]), [
        {"label": "Outreach for #1", "say": f"Write an outreach message for prospect {top['id']}."},
        {"label": "Mock-up for #1", "say": f"Mock up a home page for prospect {top['id']}."},
        {"label": "Add #1 as a lead", "say": f"Add prospect {top['id']} as a lead."}])


async def audit(settings: Settings, args: dict, http: httpx.AsyncClient) -> screen.Shown:
    rows = st.rows_of(settings, st.PROSPECTS)
    who = args.get("business") or args.get("url")
    p = st.find_prospect(rows, who)
    url = args.get("url") or (p or {}).get("website")
    if social_of(url or ""):
        raise ValueError(f"That's a {social_of(url).capitalize()} page, not a website, so there's nothing to audit. "
                         "That's the pitch: offer them their first proper website.")
    if not url:
        if p:
            raise ValueError(f"{p['name']} has no website on record, which is the pitch: offer them their first one.")
        raise ValueError("Which website should I audit? Give its address, e.g. joesbarbers.co.uk.")
    result = await with_pagespeed(settings, http, await audit_url(http, url))
    name = (p or {}).get("name") or args.get("business") or result["title"] or st.domain(result["url"])
    if p:
        p["audit"] = result
        if is_store(p):
            p["lead_type"] = STORE_LEAD
        st.save(settings, st.PROSPECTS, rows)
    else:
        p = merge(settings, [{"name": st.clean(name, 80), "kind": "business", "town": "", "website": result["url"],
                              "phone": "", "email": (result["emails"] or [""])[0], "address": "", "osm": "",
                              "audit": result, **({"lead_type": STORE_LEAD} if result.get("shopify") else {})}])[0]
    path = st.write(settings, ("Audits",), f"{st.domain(result['url']) or st.slug(name)}.md", audit_md(name, result),
                    replace=True)
    if result["grade"] == "down":
        text = f"{name}'s website at {result['url']} doesn't load ({result['problems'][0]['why']}). That's an easy pitch."
    else:
        top = "; ".join(x["problem"].lower() for x in result["problems"][:3]) or "nothing big"
        text = f"{name} scores {result['score']} out of 100 ({result['grade']}). Biggest problems: {top}."
        store = result.get("shopify")
        if store:
            text += (f" It's a Shopify store ({store['theme'] or 'theme not named'}"
                     + (", one of Shopify's free themes" if store["free_theme"] else "")
                     + (f", reviews by {store['reviews']}" if store["reviews"] else ", no reviews app")
                     + (f", PageSpeed {store['pagespeed']}/100 on phones" if store.get("pagespeed") is not None else "")
                     + "), so pitch a store makeover.")
    text += f" The full audit is in {st.where(settings, path)}."
    rows_ = [[x["problem"], f"-{x['points']}", x["why"]] for x in result["problems"]] or [["Nothing big", "0", "A strong site"]]
    redo = "a Shopify store redesign" if result.get("shopify") else "a new website"
    return st.table(text, f"Audit: {name} ({result['score']}/100)", ["Problem", "Points", "Why it matters"], rows_, [
        {"label": "Write outreach", "say": f"Write an outreach message for prospect {p['id']}."},
        {"label": "Quote a redesign", "say": f"Quote prospect {p['id']} for {redo}."}])


def prospects(settings: Settings, args: dict) -> screen.Shown:
    rows = st.rows_of(settings, st.PROSPECTS)
    if args.get("town"):
        rows = [r for r in rows if str(args["town"]).lower() in (r.get("town", "") + " " + r.get("address", "")).lower()]
    if args.get("country"):
        code = world.country_code(args["country"])
        rows = [r for r in rows if r.get("country") == code or (code == world.HOME and not r.get("country"))]
    if args.get("status"):
        rows = [r for r in rows if r.get("status") == args["status"]]
    if not rows:
        raise ValueError("No prospects saved yet. Ask me to find businesses with weak websites in a town.")
    rows.sort(key=rank_key)
    return st.table(f"{len(rows)} prospect{'s' if len(rows) != 1 else ''}, best bets first.", "Web design prospects",
                    COLUMNS, prospect_rows(rows[:60]))


def prospect(settings: Settings, args: dict) -> screen.Shown:
    p = st.find_prospect(st.rows_of(settings, st.PROSPECTS), args.get("business"))
    if not p:
        raise ValueError("I can't find that prospect. Say its number or name.")
    score, problem = headline(p)
    body = "\n".join(x for x in [
        f"{p['name']} ({p['kind']}){', ' + p['town'] if p.get('town') else ''}"
        f"{', ' + world.country_name(p['country']) if p.get('country') else ''}",
        f"Website: {p.get('website') or 'none'}  |  Score: {score}  |  Status: {p.get('status', 'new')}",
        f"Lead type: {STORE_LEAD} (theme: {p['audit']['shopify'].get('theme') or 'not named'})" if is_store(p) else "",
        f"Phone: {p['phone']}" if p.get("phone") else "", f"Email: {p['email']}" if p.get("email") else "",
        f"Address: {p['address']}" if p.get("address") else "", f"Facebook: {p['facebook']}" if p.get("facebook") else "",
        f"Instagram: {p['instagram']}" if p.get("instagram") else "", f"Google Maps: {p['maps']}" if p.get("maps") else "",
        f"Google rating: {p['rating']} ({p.get('reviews') or 0} reviews)" if p.get("rating") else "",
        "", "Problems:" if p.get("audit") else ""] + [f"- {x['problem']}: {x['why']}" for x in (p.get("audit") or {}).get("problems", [])])
    return st.text_card(f"{p['name']}: {problem.lower()}.", p["name"], body, [
        {"label": "Write outreach", "say": f"Write an outreach message for prospect {p['id']}."},
        {"label": "Mock-up", "say": f"Mock up a home page for prospect {p['id']}."}])


def add_lead(settings: Settings, args: dict) -> screen.Shown:
    import kinetic_sales  # here, not at the top: kinetic_sales imports this module
    rows = st.rows_of(settings, st.PROSPECTS)
    p = st.find_prospect(rows, args.get("business"))
    if not p:
        raise ValueError("I can't find that prospect. Say its number or name.")
    package = "shopify_redesign" if is_store(p) else "business" if p.get("website") else "starter"
    value = kinetic_sales.prices(settings)["packages"][package]["price"]
    shown = freelance_clients.lead_add(settings, {"client": p["name"], "title": "New website" if not p.get("website")
                                                  else "Shopify store redesign" if is_store(p) else "Website redesign", "value": value, "source": "Kinetic finder"})
    p["status"] = "lead"
    st.save(settings, st.PROSPECTS, rows)
    return screen.Shown(f"{p['name']} is now a lead in your freelance pipeline, worth about {st.gbp(value)}. "
                        + str(shown), shown.card)


def mark(settings: Settings, args: dict) -> str:
    rows = st.rows_of(settings, st.PROSPECTS)
    p = st.find_prospect(rows, args.get("business"))
    if not p:
        raise ValueError("I can't find that prospect. Say its number or name.")
    if args.get("status") not in STATUSES:
        raise ValueError("Mark it as one of " + ", ".join(STATUSES) + ".")
    p["status"] = args["status"]
    if args["status"] == "contacted":
        p["contacted"] = st.today().isoformat()
    st.save(settings, st.PROSPECTS, rows)
    import kinetic_outreach  # here, not at the top: it reaches kinetic_sales, which imports this module
    kinetic_outreach.from_finder(settings, p, args["status"])  # keep the outreach tracker in step
    return f"{p['name']} is now marked {args['status']}."


def forget(settings: Settings, args: dict) -> str:
    rows = st.rows_of(settings, st.PROSPECTS)
    p = st.find_prospect(rows, args.get("business"))
    if not p:
        raise ValueError("I can't find that prospect.")
    if not args.get("confirmed"):
        return f"Should I remove {p['name']} from your prospects? Say yes to confirm."
    rows.remove(p)
    st.save(settings, st.PROSPECTS, rows)
    return f"Removed {p['name']} from your prospects."


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_client_finder",
        "description": "Kinetic Web Designs client finder, to win paid website work, anywhere in the world. find: "
                       "local independent businesses (cafes, hairdressers, trades, garages, shops...) near a town or "
                       "city in any country from Google Maps (when a Places key is set) or OpenStreetMap (e.g. salons "
                       "in Lagos, barbers in Seoul), "
                       "with their websites audited and ranked best bet first (no website or only a Facebook/Instagram "
                       "page, then a broken site, then the lowest score). Shops of any kind (fashion, beauty shops, "
                       "wigs, jewellery, home and gifts, food and drink, sports shops, pet shops, kids shops, art "
                       "shops; 'online shop', 'shopify' or 'boutique' searches them all): sites on Shopify become "
                       "\"Shopify store\" leads with store checks (theme and whether it's a free one like Dawn, "
                       "reviews app, page weight, add-on scripts, movement and personality, optional PageSpeed), "
                       "ranked free theme with no movement first, then no reviews, then a heavy page. "
                       "audit: score any public website out of 100 with plain-words problems to pitch (padlock, "
                       "phones, speed, Google, tap-to-call, old footer). prospects / prospect: the saved list or one "
                       "business. mark: set a prospect's status (e.g. contacted once the user has sent their "
                       "message; web_design_outreach keeps the fuller outreach record and follow-ups). add_lead: put a prospect in the freelance lead pipeline. forget needs confirmed true "
                       "after the user says yes. Nothing is ever sent or posted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "town": {"type": "string", "description": "find: a town, city, area or postcode anywhere, e.g. "
                                                          "'Stockport', 'Lagos' or 'Seoul'. prospects: filter by town."},
                "country": {"type": "string", "description": "find: the country, when the user names one or the "
                                                             "town is ambiguous, e.g. 'Nigeria', 'South Korea', 'USA'. "
                                                             "prospects: filter by country."},
                "kind": {"type": "string", "description": "find: " + ", ".join(KINDS) + " or mixed (default: the trade "
                                                          "of the week if one is set, else mixed)."},
                "radius_km": {"type": "number", "description": "find: how far around the town, 0.5 to 15 km (default 3)."},
                "audit_limit": {"type": "integer", "description": f"find: websites to audit (default {DEFAULT_AUDITS}, "
                                                                f"max {MAX_AUDITS})."},
                "url": {"type": "string", "description": "audit: the website, e.g. 'joesbarbers.co.uk'."},
                "business": {"type": "string", "description": "A saved prospect's number or name."},
                "status": {"type": "string", "enum": STATUSES, "description": "mark: the new status. prospects: filter."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient | None = None):
    action = args.get("action")
    if action in ("find", "audit"):
        if http is None:
            async with httpx.AsyncClient() as own:
                return await run_tool(name, args, settings, own)
        return await (find if action == "find" else audit)(settings, args, http)
    return st.dispatch({"prospects": prospects, "prospect": prospect, "mark": mark, "add_lead": add_lead,
                        "forget": forget},
                       action, settings, args, "client finder")
