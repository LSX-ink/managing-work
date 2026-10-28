"""A premium mock-up from start to finish, on Alfred's say-so ("Alfred, build a mock-up for Vox in Manchester").

The steps the owner and Claude did by hand, in order: the deep dive (research.py: their website's words, photos, logo
and colours, plus the Google listing), an audit of their current site, config.json written by Claude from all that and
the photo contact sheet (only their real words, prices and reviews; in a layout the last few mock-ups didn't use), the
page itself (premium_page.py), the before/after (their homepage and this design, both on a phone), online, the full
customer-eye check (full_check.py), the Instagram name checked as a real profile, and the short DM.

Nothing is sent and no credits are used: the owner reads the DM and sends it himself. A mock-up link that was already
made is never touched; a second one for the same business goes on -v2 (owner, 26 Oct 2026)."""
import asyncio, base64, json, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
LEADS = HERE / "leads"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent / "stays"))
sys.path.insert(0, str(HERE.parent.parent))
import httpx  # noqa: E402

LAYOUTS = ["atelier", "editorial", "split", "bold", "cinema"]
FONTS = {"atelier": [None], "editorial": ["editorial", "fashion", "vintage"], "split": ["split", "fashion", "script"],
         "bold": ["bold", "cinema"], "cinema": ["cinema", "vintage"]}
EXAMPLE = LEADS / "vox-hairdressing" / "config.json"
PAGE_TEXT = 14000
COPY_GUIDE = 12000  # characters of the copywriting skill given to the writer  # characters of their website's words sent to Claude
WRITE_PROMPT = """You design premium concept websites for Kinetic Web Designs. Write config.json for one business from
its research: their website's words, their Google listing and a contact sheet of their photos (file names in red).

Rules, all strict:
- Use only what's in the research. Never invent prices, services, offers, awards, dates or facts. A service with no
  price on their site has "" as its price. If their site lists no services at all, give 3 to 6 plain service names
  that the listing or photos clearly show, with "" prices, and no currency_note.
- "special" only if their site shows a real offer; otherwise leave it out.
- Colours must match their brand: the logo and their website colours. Dark "bg" and "panel", light "ink", "muted" in
  between, "gold" is their main accent and "second" a second brand colour. Hex codes only.
- Photos: pick by file name from the contact sheet. "hero": 4 striking, sharp photos of the place or the work;
  "experience.photos": 2; "gallery": 6 to 9. Never pick logos, flyers, text-heavy images, blurry or tiny ones, or a
  photo twice. Prefer s/ (their site) over g/ (Google) when both are good.
- "logo": the best logo file from the list, or "" if none is clean; "logo_light": true when it is dark on white.
- "piece": the 3D idea for the first screen, taken from THIS business's own story (their headline, what they offer,
  their shop, their brand): neon (their name as a neon sign, for a neon shopfront or a night-time vibe), coffee (they
  offer coffee), whisky (a dram / whisky), cocktail (drinks or cocktails), banter (chat, community, good times), mirror
  (a full grooming or beauty service), bottle (their own product range; set "piece_text" to the brand name for the
  label), pole (a traditional barber's), scissors (precision cutting), razor (wet or straight-razor shaves), clipper
  (fades), comb (classic cuts), brush (styling, blow-dries), dryer (salon styling). Never one of the recent pieces
  listed below, so no two mock-ups look the same. "piece_text": the word to show, only for neon or bottle.
- Words: warm, confident, short. h1 is three short lines, the third the most striking. "kicker" is the street and area.
- "audit": {"title": "What <their domain> is costing you, and what this fixes.", "fixes": [[problem, fix], ...]}, from
  the audit problems only (2 to 4 pairs, plain English, fix said as what this design does), or {} with no website.
Answer with the JSON object only, keys as in the example."""


def copy_guide() -> str:
    """The copywriting skill (skills/marketing/copywriting, MIT) for every word on the page, when it's there."""
    guide = HERE.parent.parent / "skills" / "marketing" / "copywriting" / "SKILL.md"
    try:
        text = guide.read_text(encoding="utf-8")
    except OSError:
        return ""
    return ("\n\nWrite every word by this copywriting guide (the rules above still win: their real facts only):\n\n"
            + text[:COPY_GUIDE])


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "mock-up"


def free_slug(base: str, live: Path) -> str:
    """The base name, or -v2, -v3... when a mock-up with that name was already made (sent links never change)."""
    slug, n = base, 1
    while (live / "m" / slug).exists() or (LEADS / slug / "config.json").exists():
        n += 1
        slug = f"{base}-v{n}"
    return slug


def next_piece(name: str, types=(), leads: Path = LEADS) -> str:
    """The 3D piece for a new mock-up: one that fits the trade, the least used so far (owner, 28 Oct 2026: "why is the
    3d the same for every website thats terrible marketing"), so neighbouring mock-ups never share one."""
    import depth3d
    order = depth3d.pieces_for(name, types)
    used = Counter(json.load(open(f, encoding="utf-8")).get("piece") for f in leads.glob("*/config.json"))
    return min(order, key=lambda pc: (used[pc], order.index(pc)))


def next_layout(leads: Path = LEADS) -> str:
    """The layout used least so far, newest-used last among ties, so each mock-up looks different."""
    configs = sorted(leads.glob("*/config.json"), key=lambda f: f.stat().st_mtime)
    used = [json.load(open(f, encoding="utf-8")).get("layout", "atelier") for f in configs]
    count = Counter(used)
    last = {lay: i for i, lay in enumerate(used)}
    return min(LAYOUTS, key=lambda lay: (count[lay], last.get(lay, -1)))


def listing_facts(place: dict, instagram: str, website: str) -> dict:
    """What comes straight from Google, word for word: never left to the writer."""
    hours = []
    for line in (place.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []:
        day, _, time = line.partition(": ")
        hours.append([day, re.sub(r"[  ]", " ", time).replace(" � ", " – ").replace("�", "–")])
    reviews = [[r["text"]["text"].replace("\n", " ").strip(), (r.get("authorAttribution") or {}).get("displayName", "")]
               for r in place.get("reviews") or [] if (r.get("text") or {}).get("text") and r.get("rating", 5) >= 4][:6]
    loc = place.get("location") or {}
    stats = []
    if place.get("rating"):
        stats += [[f"{place['rating']:.1f}", "Google rating"], [f"{place.get('userRatingCount', 0):,}", "Google reviews"]]
    return {"name": place["displayName"]["text"], "phone": place.get("nationalPhoneNumber", ""),
            "address": place.get("formattedAddress", ""), "hours": hours, "reviews": reviews, "stats": stats,
            "loc": [loc.get("latitude"), loc.get("longitude")] if loc else None, "instagram": instagram.strip("@"),
            "book_url": website, "book_label": "Book now" if website else "Call us"}


def recent_pieces(n: int = 8, leads: Path = LEADS) -> list[str]:
    """The 3D ideas the last few mock-ups used: a new one may not repeat them."""
    configs = sorted(leads.glob("*/config.json"), key=lambda f: f.stat().st_mtime)[-n:]
    return [pc for pc in (json.load(open(f, encoding="utf-8")).get("piece") for f in configs) if pc]


async def write_config(client, model: str, folder: Path, layout: str, fonts: str | None, audit: dict, facts: dict,
                       recent: list[str] | None = None) -> dict:
    """Claude writes config.json from the research; the Google facts are put back word for word afterwards."""
    site = json.load(open(folder / "site.json", encoding="utf-8"))
    words = "\n\n".join(f"[{u}]\n{t}" for u, t in site["pages"].items())[:PAGE_TEXT]
    photos = sorted(str(p.relative_to(folder)).replace("\\", "/") for p in [*folder.glob("s/*.jpg"), *folder.glob("g/*.jpg")])
    example = json.load(open(EXAMPLE, encoding="utf-8"))
    for k in ("audit", "layout", "fonts"):
        example.pop(k, None)
    light = layout == "editorial"
    ask = (f"Layout: {layout}." + (" It is a LIGHT page: also give colours paper (the page), text (the words), soft "
                                   "(secondary words: a mid grey that still reads on paper, 4.5:1), rule (thin lines) "
                                   "and a darker gold that reads on paper." if light else "")
           + f"\n\nExample config (another business, for the format only):\n{json.dumps(example, ensure_ascii=False)[:6000]}"
           + f"\n\nTheir Google listing facts (used as they are): {json.dumps(facts, ensure_ascii=False)[:3000]}"
           + f"\n\nTheir website colours, most used first: {site['colours'][:10]}\nLogo files: {site['logos']}"
           + f"\nPhoto files: {photos}\n\nAudit of their current website: {json.dumps(audit, ensure_ascii=False)[:2000]}"
           + f"\n\nRecent 3D pieces (don't repeat): {recent or []}"
           + f"\n\nTheir website's words:\n{words or '(no website)'}")
    content = [{"type": "text", "text": ask}]
    sheet = folder / "sheet.jpg"
    if sheet.exists():
        content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                       "data": base64.b64encode(sheet.read_bytes()).decode()}})
    r = await client.messages.create(model=model, max_tokens=8000, system=WRITE_PROMPT + copy_guide(),
                                     messages=[{"role": "user", "content": content}])
    text = "".join(getattr(b, "text", "") for b in r.content)
    c = json.loads(text[text.index("{"): text.rindex("}") + 1])
    return tidy(c, folder, photos, layout, fonts, facts)


def usable_image(path: Path) -> bool:
    from PIL import Image
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:  # noqa: BLE001 - missing, SVG, broken: all mean "don't use it"
        return False


def _lum(hex_: str) -> float:
    rgb = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in rgb]
    return .2126 * r + .7152 * g + .0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + .05) / (lo + .05)


def _mix(a: str, b: str, t: float) -> str:
    return "#" + "".join(f"{round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t):02x}" for i in (1, 3, 5))


def readable(fg: str, bg: str, strong: str, need: float = 4.5) -> str:
    """fg, moved toward the strong text colour only as far as it takes to read on bg (web-design-guidelines: 4.5:1).
    Owner, 27 Oct 2026: two editorial mock-ups came out with near-white words on a near-white page."""
    for step in range(11):
        c = _mix(fg, strong, step / 10)
        if contrast(c, bg) >= need:
            return c
    return strong


HEX = re.compile(r"#[0-9a-fA-F]{6}")


def fix_contrast(col: dict, layout: str) -> dict:
    col = dict(col)
    if layout == "editorial":
        paper, text = col.get("paper", "#f6f1ea"), col.get("text", "#1d1a17")
        if HEX.fullmatch(paper) and HEX.fullmatch(text):
            col["text"] = readable(text, paper, "#000000", 7)
            col["soft"] = readable(col["soft"] if HEX.fullmatch(col.get("soft", "")) else "#6c645b", paper, col["text"])
    for bg in ("bg", "panel"):
        if all(HEX.fullmatch(col.get(k, "")) for k in (bg, "ink", "muted")):
            col["ink"] = readable(col["ink"], col[bg], "#ffffff", 7)
            col["muted"] = readable(col["muted"], col[bg], col["ink"])
    return col


def tidy(c: dict, folder: Path, photos: list[str], layout: str, fonts: str | None, facts: dict) -> dict:
    """Google's facts back word for word, only real photo files and each one once, the chosen layout and fonts, and
    text colours that read."""
    if isinstance(c.get("colours"), dict):
        c["colours"] = fix_contrast(c["colours"], layout)
    c.update({k: v for k, v in facts.items() if v})  # Google's own words win
    c["short"] = c.get("short") or facts["name"]
    used: set[str] = set()
    def fresh(picks):  # real files, each photo once across the page
        out = [p for p in dict.fromkeys(picks or []) if p in photos and p not in used]
        used.update(out)
        return out
    c["hero"] = fresh(c.get("hero"))
    c.setdefault("experience", {})["photos"] = fresh(c.get("experience", {}).get("photos"))
    c["gallery"] = fresh(c.get("gallery"))
    if len(c["gallery"]) < 6:  # top it up with photos not used yet
        c["gallery"] += fresh([p for p in photos if p not in used])[:6 - len(c["gallery"])]
    if c.get("logo") and not usable_image(folder / c["logo"]):
        c["logo"] = ""  # missing, or a format the page builder can't read (an SVG logo, say)
    if layout != "atelier":
        c["layout"] = layout
    if fonts:
        c["fonts"] = fonts
    return c


REVIEW_PROMPT = """You are the design director at Kinetic Web Designs, reviewing a concept website before it goes to the
business. You have every one of our design skills below: use ALL of them. Look at the screenshots (desktop top, desktop
further down, phone) and the config that made the page, then improve the config.

You may change only these keys: kicker, h1, lead, colours, experience (title, text, photos), hero, gallery, fonts,
logo_light, motif, currency_note, services (group names and service names, never prices), special (only to remove it).
Keep every fact true: never invent prices, offers, awards or claims. Photos only from the list given. Fonts only from
the presets given. Colours must still match the business's brand. The layouts are fixed: h1 is always exactly three
short lines (make each one count rather than dropping one), and kicker stays a short line.

Answer with JSON only: {"changes": {key: new value, ...}, "notes": ["what you changed and which skill said so", ...]}.
Return {"changes": {}, "notes": [...]} when it is already excellent."""
SHAPES = {  # what the page layouts read: h1 is always three lines, the rest keeps its form
    "h1": lambda v: isinstance(v, list) and len(v) == 3 and all(isinstance(x, str) and x.strip() for x in v),
    "kicker": lambda v: isinstance(v, str), "lead": lambda v: isinstance(v, str) and v.strip(),
    "colours": lambda v: isinstance(v, dict) and all(isinstance(v.get(k), str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v[k])
                                                     for k in ("bg", "panel", "ink", "muted", "gold")),
    "experience": lambda v: isinstance(v, dict) and isinstance(v.get("title"), str) and isinstance(v.get("text"), str),
    "hero": lambda v: isinstance(v, list) and len(v) >= 1, "gallery": lambda v: isinstance(v, list) and len(v) >= 3,
    "services": lambda v: isinstance(v, list) and all(isinstance(g, dict) and isinstance(g.get("items"), list) for g in v),
}
REVIEW_TRIES = 3
REVIEW_KEYS = {"kicker", "h1", "lead", "colours", "experience", "hero", "gallery", "fonts", "logo_light", "motif",
               "currency_note", "services", "special"}


async def page_shots(page: Path) -> list[bytes]:
    """The built page as a customer first sees it: desktop top, desktop further down, phone top."""
    from playwright.async_api import async_playwright
    shots = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        try:
            for view, mobile in (({"width": 1280, "height": 800}, False), ({"width": 390, "height": 800}, True)):
                pg = await b.new_page(viewport=view, is_mobile=mobile, has_touch=mobile)
                await pg.goto(page.as_uri(), wait_until="domcontentloaded", timeout=45000)
                await pg.wait_for_timeout(5000)
                shots.append(await pg.screenshot(type="jpeg", quality=60))
                if not mobile:
                    h = await pg.evaluate("document.body.scrollHeight")
                    for y in range(0, int(h * .4), 500):  # scroll so sections reveal themselves
                        await pg.evaluate(f"scrollTo(0,{y})")
                        await pg.wait_for_timeout(120)
                    await pg.wait_for_timeout(1500)
                    shots.append(await pg.screenshot(type="jpeg", quality=60))
                await pg.close()
        finally:
            await b.close()
    return shots


async def review(client, model: str, folder: Path, page: Path, c: dict, layout: str, facts: dict) -> tuple[dict, list[str]]:
    """The design review with every website skill (owner, 27 Oct 2026: "always use all the skills so you get the best
    version"). Returns the improved config and the notes; on any failure, the config as it was."""
    import design  # noqa: E402 - Alfred's skills library
    import layouts  # noqa: E402
    photos = sorted(str(p.relative_to(folder)).replace("\\", "/") for p in [*folder.glob("s/*.jpg"), *folder.glob("g/*.jpg")])
    try:
        shots = await page_shots(page)
        shown = {k: v for k, v in c.items() if k not in ("reviews", "hours", "loc", "audit")}
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                "data": base64.b64encode(s).decode()}} for s in shots]
        content.append({"type": "text", "text": f"Layout: {layout}. Font presets: {sorted(layouts.FONTS)}.\nPhoto "
                        f"files: {photos}\n\nConfig:\n{json.dumps(shown, ensure_ascii=False)}"})
        system = REVIEW_PROMPT + "\n\nOUR DESIGN SKILLS:\n\n" + design.website_pack()
        for attempt in range(REVIEW_TRIES):  # a reply that isn't clean JSON is asked for again (Capello, 27 Oct 2026)
            r = await client.messages.create(model=model, max_tokens=8000, system=system,
                                             messages=[{"role": "user", "content": content}])
            text = "".join(getattr(b, "text", "") for b in r.content)
            try:
                out = json.loads(text[text.index("{"): text.rindex("}") + 1])
                break
            except ValueError:
                if attempt == REVIEW_TRIES - 1:
                    raise
    except Exception as exc:  # noqa: BLE001 - the page as written is still good to go
        return c, [f"design review skipped ({type(exc).__name__}: {str(exc)[:120]})"]
    changes = {k: v for k, v in (out.get("changes") or {}).items() if k in REVIEW_KEYS}
    if "special" in changes and changes["special"]:
        del changes["special"]  # it may only take an offer away, never add one
    if "services" in changes and not same_prices(c.get("services"), changes["services"]):
        del changes["services"]  # prices are facts: a rename that moves or changes them is dropped
    if "fonts" in changes and changes["fonts"] not in [f for f in FONTS.get(layout, []) if f]:
        del changes["fonts"]  # only the type made for this layout (vintage on the bold layout came out messy, 28 Oct)
    for key in ("colours", "experience"):  # a partial change keeps the rest
        if isinstance(changes.get(key), dict) and isinstance(c.get(key), dict):
            changes[key] = {**c[key], **changes[key]}
    for key, ok in SHAPES.items():  # the layouts need these shapes: a review that changes one is kept out
        if key in changes and not ok(changes[key]):
            del changes[key]
    new = {**c, **changes}
    if "special" in changes:
        new.pop("special", None)
    return tidy(new, folder, photos, layout, new.get("fonts"), facts), [str(n) for n in out.get("notes") or []]


def same_prices(old, new) -> bool:
    """True when every price is unchanged and in the same order (names may differ, groups may be split or joined)."""
    try:
        return [str(i[1]) for g in old or [] for i in g["items"]] == [str(i[1]) for g in new or [] for i in g["items"]]
    except (KeyError, IndexError, TypeError):
        return False


async def phone_shots(their_url: str, ours: Path, folder: Path) -> bool:
    """before.jpg (their homepage) and after.jpg (this design), each the first screen on a phone."""
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        try:
            for url, name in ((their_url, "before.jpg"), (ours.as_uri(), "after.jpg")):
                pg = await b.new_page(viewport={"width": 390, "height": 760}, device_scale_factor=600 / 390, is_mobile=True)
                await pg.goto(url, wait_until="domcontentloaded", timeout=45000)
                await pg.wait_for_timeout(6000)
                for label in ("Reject all", "Reject", "Decline", "Only necessary", "Necessary only"):  # cookie banners
                    btn = pg.get_by_role("button", name=label, exact=True)
                    if await btn.count() and await btn.first.is_visible():
                        await btn.first.click(timeout=2000)
                        await pg.wait_for_timeout(1500)
                        break
                await pg.screenshot(path=str(folder / name), type="jpeg", quality=82)
                await pg.close()
        except Exception as exc:  # a site that won't load just means no before/after
            print(f"before/after skipped: {exc!r}", flush=True)
            return False
        finally:
            await b.close()
    return True


async def make(business: str, settings, client, website: str = "", instagram: str = "", progress=print) -> dict:
    """Build, check and put online one premium mock-up. Returns {slug, link, dm, issues, instagram_ok, ...}."""
    import depth3d, full_check, kinetic_find, outbox, premium_page, research  # noqa: E401 - heavy, so only when building
    base = slugify(re.split(r",| in ", business)[0])
    slug = free_slug(base, outbox.LIVE)
    folder = LEADS / slug
    progress(f"Researching {business}…")
    await research.main(slug, business, website)
    place = json.load(open(folder / "place.json", encoding="utf-8"))
    website = website or place.get("websiteUri", "")
    async with httpx.AsyncClient(timeout=30, headers=outbox.UA) as http:
        audit = {}
        if website and "instagram.com" not in website:
            try:
                audit = await kinetic_find.audit_url(http, website)
            except Exception as exc:  # noqa: BLE001 - no audit just means no fixes list
                audit = {"error": str(exc)}
        p = {"name": place["displayName"]["text"], "website": website, "rating": place.get("rating"),
             "reviews": place.get("userRatingCount")}
        instagram = (instagram or await outbox.instagram_handle(http, p) or "").strip("@")
    layout = next_layout()
    fonts = FONTS[layout][len(list(LEADS.glob("*/config.json"))) % len(FONTS[layout])]
    progress(f"Writing the {layout} design…")
    model = getattr(settings, "big_model", "") or "claude-opus-5"
    writer = getattr(client, "direct", client)  # the design needs Claude's eyes on the photos, not the free route
    facts = listing_facts(place, instagram, website)
    recent = recent_pieces()
    c = await write_config(writer, model, folder, layout, fonts, audit, facts, recent)
    c["depth3d"] = True  # a 3D piece of their trade over the first screen (depth3d.py; owner, 28 Oct 2026)
    if c.get("piece") not in depth3d.PIECES or c["piece"] in recent:   # the writer's idea, unless it isn't new
        c["piece"] = next_piece(p["name"], place.get("types") or ())
        c.pop("piece_text", None)
    json.dump(c, open(folder / "config.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    out = outbox.LIVE / "m" / slug
    await asyncio.to_thread(premium_page.build, folder, out)
    progress("Reviewing the design with every one of our design skills…")
    c, notes = await review(writer, model, folder, out / "index.html", c, layout, facts)
    (folder / "review.md").write_text("# Design review (every website skill)\n\n" + "".join(f"- {n}\n" for n in notes),
                                      encoding="utf-8")
    json.dump(c, open(folder / "config.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    await asyncio.to_thread(premium_page.build, folder, out)
    if website and "instagram.com" not in website and await phone_shots(website, out / "index.html", folder):
        await asyncio.to_thread(premium_page.build, folder, out)  # again, now with the before/after
    progress("Putting it online and checking it like a customer would…")
    await asyncio.to_thread(outbox.deploy_site)
    link = f"https://kineticwebdesigns.co.uk/m/{slug}/"
    issues = await check_live(slug)
    if any("folder missing" in i for i in issues):  # Cloudflare sometimes needs a second push before new files show
        await asyncio.to_thread(outbox.deploy_site)
        issues = await check_live(slug)
    ig_ok = bool(instagram) and await outbox.instagram_exists(instagram)
    return {"slug": slug, "name": p["name"], "link": link, "layout": layout, "issues": issues, "instagram": instagram,
            "instagram_ok": ig_ok, "dm": outbox.dm_text(settings, p, link), "review": notes,
            "audit": {k: audit.get(k) for k in ("score", "grade") if isinstance(audit, dict)}}


async def check_live(slug: str) -> list[str]:
    import full_check
    from playwright.async_api import async_playwright
    async with async_playwright() as pw, httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as http:
        b = await pw.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        try:
            return (await full_check.check(b, http, slug))[1]
        finally:
            await b.close()


if __name__ == "__main__":  # python auto.py "Business name, Town" [website] [instagram]
    import config
    import omniroute
    args = sys.argv[1:] + ["", ""]
    result = asyncio.run(make(args[0], config.settings, omniroute.make_client(config.settings), args[1], args[2]))
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, indent=1, ensure_ascii=False))
