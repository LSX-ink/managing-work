"""Kinetic Web Designs client finder: find local businesses with no website or a weak one, and audit any website.

find: looks a town up on OpenStreetMap (Nominatim), lists independent businesses of a kind near it (Overpass API; big
chains with a brand tag are skipped), then audits the websites of the first few. The results are ranked best bet first:
no website, then a website that doesn't load, then the lowest score. They're kept in kinetic-prospects.json and written
up as a report in Kinetic Web Designs/Prospects.

audit: reads one public website with plain HTTP (no scripts run, nothing is sent) and scores it out of 100 on what a
small business owner would care about: the padlock, working on phones, speed, being found on Google, tap-to-call, a
way to get in touch, an out-of-date footer, share previews and very old tech. Each problem comes with a plain-words
reason to use in a pitch. The report goes in Kinetic Web Designs/Audits/<domain>.md.

Every link is checked with memory.check_public (through design_extract.fetch), so a page can't steer Alfred into this
PC or the home network. OpenStreetMap is volunteer-made, so some businesses are missing or out of date.
"""

import asyncio
import re
import time
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

import design_extract
import freelance_clients
import kinetic_store as st
import screen
from config import Settings

NAMES = {"web_client_finder"}
ACTIONS = ["find", "audit", "prospects", "prospect", "mark", "add_lead", "forget"]
STATUSES = ["new", "lead", "contacted", "client", "not interested"]
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = "https://overpass-api.de/api/interpreter"
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
        try:
            final, kind, markup = await design_extract.fetch(http, attempt, MAX_HTML)
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
        return score_page(final, markup, seconds, len(markup.encode("utf-8", "ignore")),
                          urlparse(final).scheme == "https", st.today().year)
    return down(https_url, last)


def audit_md(name: str, a: dict) -> str:
    lines = [f"# Website audit: {name}", "", f"{a['url']} checked by Alfred on {a['date']}.", "",
             f"**Score: {a['score']}/100 ({a['grade']})**", ""]
    if a.get("builder"):
        lines += [f"Built with: {a['builder']}", ""]
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


def business_of(element: dict, town: str) -> dict | None:
    tags = element.get("tags") or {}
    name = st.clean(tags.get("name"), 80)
    if not name or tags.get("brand") or tags.get("brand:wikidata") or tags.get("disused") == "yes":
        return None  # chains have a brand tag and hire agencies, not local designers
    website = tags.get("website") or tags.get("contact:website") or tags.get("url") or ""
    address = ", ".join(x for x in (" ".join(filter(None, (tags.get("addr:housenumber"), tags.get("addr:street")))),
                                    tags.get("addr:city"), tags.get("addr:postcode")) if x)
    return {"name": name, "kind": kind_label(tags), "town": town, "website": st.clean(website, 200),
            "phone": st.clean(tags.get("phone") or tags.get("contact:phone"), 40),
            "email": st.clean(tags.get("email") or tags.get("contact:email"), 80), "address": st.clean(address, 160),
            "facebook": st.clean(tags.get("contact:facebook") or tags.get("facebook"), 200),
            "osm": f"{element.get('type', '')}/{element.get('id', '')}"}


async def geocode(http: httpx.AsyncClient, place: str) -> tuple[float, float, str]:
    try:
        r = await http.get(NOMINATIM, params={"q": place, "format": "jsonv2", "limit": 1}, headers=OSM_HEADERS,
                           timeout=15)
        r.raise_for_status()
        found = r.json()
    except (httpx.HTTPError, ValueError):
        raise ValueError("I couldn't look that place up on the map right now; try again in a minute.") from None
    if not found:
        raise ValueError(f"I couldn't find {place} on the map. Try a town and county, or a postcode.")
    hit = found[0]
    return float(hit["lat"]), float(hit["lon"]), st.clean(hit.get("display_name", place).split(",")[0], 60)


async def nearby(http: httpx.AsyncClient, lat: float, lon: float, radius: int, kind: str, town: str) -> list[dict]:
    try:
        r = await http.post(OVERPASS, data={"data": overpass_query(lat, lon, radius, kind)}, headers=OSM_HEADERS,
                            timeout=40)
        r.raise_for_status()
        elements = r.json().get("elements", [])
    except (httpx.HTTPError, ValueError):
        raise ValueError("The OpenStreetMap business search is busy; try again in a minute.") from None
    out, seen = [], set()
    for e in elements:
        b = business_of(e, town)
        if b and (key := (b["name"].lower(), b["address"].lower())) not in seen:
            seen.add(key)
            out.append(b)
    return out


def rank_key(p: dict):
    a = p.get("audit")
    if not p.get("website"):
        return (0, 0 if p.get("phone") or p.get("email") else 1, p["name"])
    if not a:
        return (3, 0, p["name"])
    if a["grade"] == "down":
        return (1, 0, p["name"])
    return (2, a["score"], p["name"])


def headline(p: dict) -> tuple[str, str]:
    """(score text, top problem) for a prospect."""
    if not p.get("website"):
        return "no site", "No website" + (" (Facebook only)" if p.get("facebook") else "")
    a = p.get("audit")
    if not a:
        return "not checked", "-"
    if a["grade"] == "down":
        return "down", "Website doesn't load"
    return f"{a['score']}/100", a["problems"][0]["problem"] if a["problems"] else "Strong site"


def merge(settings: Settings, found: list[dict]) -> list[dict]:
    """Add or refresh prospects in kinetic-prospects.json; returns the stored rows for found."""
    rows = st.rows_of(settings, st.PROSPECTS)
    out = []
    for b in found:
        hit = next((r for r in rows if b.get("osm") and r.get("osm") == b["osm"]), None) or \
            next((r for r in rows if r["name"].lower() == b["name"].lower() and
                  (r.get("address", "").lower() == b.get("address", "").lower() or
                   st.domain(r.get("website")) == st.domain(b.get("website")) != "")), None)
        if hit:
            hit.update({k: v for k, v in b.items() if v})
        else:
            if len(rows) >= st.MAX_ROWS:
                break
            hit = {"id": st.next_id(rows), "status": "new", "found": st.today().isoformat(), **b}
            rows.append(hit)
        out.append(hit)
    st.save(settings, st.PROSPECTS, rows)
    return out


def report_md(town: str, kind: str, rows: list[dict]) -> str:
    lines = [f"# Web design prospects: {kind} near {town}", "", f"Found by Alfred on {st.today().isoformat()} from "
             "OpenStreetMap. Best bets first. Check each business is still trading before you contact them.", "",
             "| # | Business | Type | Website | Score | Biggest problem | Phone | Address |",
             "|---|---|---|---|---|---|---|---|"]
    for p in rows:
        score, problem = headline(p)
        cells = [str(p["id"]), p["name"], p["kind"], p.get("website") or "none", score, problem, p.get("phone") or "-",
                 p.get("address") or "-"]
        lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    lines += ["", "Say \"audit <business>\" for the full report, \"write outreach for <business>\" for a first "
              "message, or \"mock up a home page for <business>\" for a free sample to win them over.", ""]
    return "\n".join(lines)


def prospect_rows(rows: list[dict]) -> list[list[str]]:
    out = []
    for p in rows:
        score, problem = headline(p)
        out.append([str(p["id"]), p["name"], p["kind"], st.domain(p.get("website")) or "none", score, problem,
                    p.get("status", "new")])
    return out


COLUMNS = ["#", "Business", "Type", "Website", "Score", "Biggest problem", "Status"]


async def find(settings: Settings, args: dict, http: httpx.AsyncClient) -> screen.Shown:
    place = st.need(args.get("town"), "town or postcode", 80)
    kind = kind_key(args.get("kind"))
    radius = int(min(max(st.number(args.get("radius_km") or 3, "distance"), 0.5), 15) * 1000)
    lat, lon, town = await geocode(http, place)
    found = await nearby(http, lat, lon, radius, kind, town)
    if not found:
        raise ValueError(f"OpenStreetMap has no independent {kind} listed within {radius // 1000} km of {town}. "
                         "Try a bigger distance or another kind of business.")
    limit = int(min(max(int(args.get("audit_limit") or DEFAULT_AUDITS), 0), MAX_AUDITS))
    to_check = [b for b in found if b["website"]][:limit]
    gate = asyncio.Semaphore(4)

    async def check(b):
        async with gate:
            try:
                b["audit"] = await audit_url(http, b["website"])
            except ValueError as e:
                b["audit"] = down(b["website"], str(e))

    await asyncio.gather(*(check(b) for b in to_check))
    rows = sorted(merge(settings, found), key=rank_key)
    label = "businesses" if kind == "mixed" else kind
    path = st.write(settings, ("Prospects",), f"{town} {label} {st.today().isoformat()}.md", report_md(town, label, rows),
                    replace=True)
    none = sum(1 for p in rows if not p.get("website"))
    weak = sum(1 for p in rows if p.get("audit") and p["audit"]["grade"] in ("weak", "down"))
    unchecked = sum(1 for p in rows if p.get("website") and not p.get("audit"))
    best = [f"{p['name']} ({headline(p)[1].lower()})" for p in rows[:3]]
    text = (f"I found {len(rows)} independent {label} near {town}: {none} with no website and {weak} with a weak or "
            f"broken one. Best bets: {', '.join(best)}.")
    if unchecked:
        text += f" I didn't check {unchecked} other website{'s' if unchecked != 1 else ''}; ask me to audit any of them."
    text += f" The list is saved in {st.where(settings, path)}."
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
    if not url:
        if p:
            raise ValueError(f"{p['name']} has no website on record, which is the pitch: offer them their first one.")
        raise ValueError("Which website should I audit? Give its address, e.g. joesbarbers.co.uk.")
    result = await audit_url(http, url)
    name = (p or {}).get("name") or args.get("business") or result["title"] or st.domain(result["url"])
    if p:
        p["audit"] = result
        st.save(settings, st.PROSPECTS, rows)
    else:
        p = merge(settings, [{"name": st.clean(name, 80), "kind": "business", "town": "", "website": result["url"],
                              "phone": "", "email": (result["emails"] or [""])[0], "address": "", "osm": "",
                              "audit": result}])[0]
    path = st.write(settings, ("Audits",), f"{st.domain(result['url']) or st.slug(name)}.md", audit_md(name, result),
                    replace=True)
    if result["grade"] == "down":
        text = f"{name}'s website at {result['url']} doesn't load ({result['problems'][0]['why']}). That's an easy pitch."
    else:
        top = "; ".join(x["problem"].lower() for x in result["problems"][:3]) or "nothing big"
        text = f"{name} scores {result['score']} out of 100 ({result['grade']}). Biggest problems: {top}."
    text += f" The full audit is in {st.where(settings, path)}."
    rows_ = [[x["problem"], f"-{x['points']}", x["why"]] for x in result["problems"]] or [["Nothing big", "0", "A strong site"]]
    return st.table(text, f"Audit: {name} ({result['score']}/100)", ["Problem", "Points", "Why it matters"], rows_, [
        {"label": "Write outreach", "say": f"Write an outreach message for prospect {p['id']}."},
        {"label": "Quote a redesign", "say": f"Quote prospect {p['id']} for a new website."}])


def prospects(settings: Settings, args: dict) -> screen.Shown:
    rows = st.rows_of(settings, st.PROSPECTS)
    if args.get("town"):
        rows = [r for r in rows if str(args["town"]).lower() in (r.get("town", "") + " " + r.get("address", "")).lower()]
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
        f"{p['name']} ({p['kind']}){', ' + p['town'] if p.get('town') else ''}",
        f"Website: {p.get('website') or 'none'}  |  Score: {score}  |  Status: {p.get('status', 'new')}",
        f"Phone: {p['phone']}" if p.get("phone") else "", f"Email: {p['email']}" if p.get("email") else "",
        f"Address: {p['address']}" if p.get("address") else "", f"Facebook: {p['facebook']}" if p.get("facebook") else "",
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
    package = "business" if p.get("website") else "starter"
    value = kinetic_sales.prices(settings)["packages"][package]["price"]
    shown = freelance_clients.lead_add(settings, {"client": p["name"], "title": "New website" if not p.get("website")
                                                  else "Website redesign", "value": value, "source": "Kinetic finder"})
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
        "description": "Kinetic Web Designs client finder, to win paid website work. find: local independent "
                       "businesses (cafes, hairdressers, trades, garages, shops...) near a town from OpenStreetMap, "
                       "with their websites audited and ranked best bet first (no website, broken site, lowest score). "
                       "audit: score any public website out of 100 with plain-words problems to pitch (padlock, "
                       "phones, speed, Google, tap-to-call, old footer). prospects / prospect: the saved list or one "
                       "business. mark: set a prospect's status (e.g. contacted once the user has sent their "
                       "message). add_lead: put a prospect in the freelance lead pipeline. forget needs confirmed true "
                       "after the user says yes. Nothing is ever sent or posted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "town": {"type": "string", "description": "find: a town, area or postcode, e.g. 'Stockport'. "
                                                          "prospects: filter by town."},
                "kind": {"type": "string", "description": "find: " + ", ".join(KINDS) + " or mixed (default)."},
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
