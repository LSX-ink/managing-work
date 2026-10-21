"""Kinetic Web Designs reach: one trade a week, its base mock-up, walk-in routes and mock-up videos.

trade_of_week: "this week is barbers" sets the trade of the week (kept in kinetic-trade-week.json). The client finder
and outreach then use it whenever no trade or lead is named, anywhere in the world. Setting it builds ONE base mock-up
design for that trade, once (kinetic_sales' mock-up generator with placeholders in it), saved in Kinetic Web
Designs/Trade bases. Every lead of that trade then gets their mock-up from the base in an instant, with their business
name, colours (from a design system saved for their website or colours saved on the prospect, else the trade's own
palette), phone, address, town and services swapped in.

walk_in_route: up to 10 nearby leads with no website (or only a Facebook or Instagram page) in a town, of the trade of
the week unless another is given, in walking order: a simple nearest-neighbour route from their map position when the
finder saved one, otherwise sorted by street and number. Each stop gets a one-paragraph walk-in script (their biggest
problem, "so I made you this", "see your design before you pay anything") and its mock-up. Walk-ins are fine under
every country's rules for cold messages, which is why it suits sole traders (UK PECR) and places where cold email
needs consent (Germany, Austria, Canada...). Saved in Kinetic Web Designs/Walk-in routes.

video: the 30-second phone video of a lead's mock-up (kinetic_video), made on its own.

Nothing here sends a message: scripts and drafts are for the user to use themselves.
"""

import asyncio
import math
import re
from html import escape

import kinetic_find
import kinetic_outreach as tracker
import kinetic_sales as ks
import kinetic_store as st
import kinetic_video
import kinetic_world as world
import screen
from config import Settings

NAMES = {"web_design_reach"}
ACTIONS = ["trade_of_week", "walk_in_route", "video"]
CLEAR_WORDS = ("none", "off", "clear", "nothing", "no trade", "stop", "any", "mixed")
KIND_TRADES = {"cafes": "cafe", "restaurants": "restaurant", "takeaways": "restaurant", "pubs": "restaurant",
               "hairdressers": "hairdresser", "beauty": "beauty", "trades": "trade", "garages": "garage",
               "shops": "shop", "fitness": "fitness", "health": "health", "cleaners": "business",
               "hotels": "business"}
ROUTE_STOPS = 10
# Placeholders in a base design, swapped for each lead's details
NAME, TOWN, PHONE, ADDRESS = "KWDNAME", "KWDTOWN", "+99999999999", "KWDADDRESS"
SLOTS = [f"KWDSERVICE{i}" for i in range(1, 7)]
COLOURS = {"bg": "KWDBG", "ink": "KWDINK", "brand": "KWDBRAND", "accent": "KWDACCENT"}


# ---- trade of the week and its base design -------------------------------------------

def base_path(settings: Settings, trade: str):
    return st.folder(settings, "Trade bases") / f"{trade} base.html"


def palette(trade: str) -> dict:
    bg, ink, brand, accent = ks.TRADE_LOOKS[trade][:4]
    return {"bg": bg, "ink": ink, "brand": brand, "accent": accent}


def build_base(settings: Settings, trade: str, style_from: str = "") -> object:
    """The trade's ONE base design: the mock-up generator run once with placeholders, plus a preview copy."""
    look = ks.look_from(settings, style_from) or {}
    head, body = ks.TRADE_LOOKS[trade][4:6]
    html = ks.mockup_html(NAME, trade, "", SLOTS, PHONE, TOWN, {**COLOURS, "head": look.get("head") or head,
                                                                 "body": look.get("body") or body},
                          st.business(settings)["name"], address=ADDRESS)
    colours = palette(trade)
    if look:  # the saved design system's colours become the trade's defaults
        colours = {k: ks.safe_css(look.get(k), v) for k, v in colours.items()}
    path = base_path(settings, trade)
    path.write_text(html, encoding="utf-8")
    st.save(settings, f"kinetic-base-{trade}.json", {"trade": trade, "made": st.today().isoformat(),
                                                     "style_from": style_from, "colours": colours})
    preview = personalise(html, "Your Business", "", "", "", ks.SERVICES[trade], colours, trade)
    st.write(settings, ("Trade bases",), f"{trade} base preview.html", preview, replace=True)
    return path


def personalise(base: str, name: str, town: str, phone: str, address: str, services: list[str], colours: dict,
                trade: str) -> str:
    """A lead's own mock-up from the trade's base: their name, colours, phone, address, town and services."""
    e = escape
    html = base.replace(ks.call_button(PHONE), ks.call_button(phone))
    html = html.replace(ks.contact_text(ADDRESS), ks.contact_text(address))
    for slot, service in zip(SLOTS, list(services[:len(SLOTS)]) + [""] * len(SLOTS)):
        html = html.replace(ks.service_card(slot), ks.service_card(service) if service else "")
    html = html.replace(f" in {TOWN}", f" in {e(town)}" if town else "")
    fallback = palette(trade)
    for key, token in COLOURS.items():
        html = html.replace(token, ks.safe_css(colours.get(key), fallback[key]))
    return html.replace(NAME, e(name))


def lead_colours(settings: Settings, p: dict, trade: str, base: dict) -> dict:
    """Their own colours when known (saved on the prospect, or a design system extracted from their website), else
    the base design's (the trade palette)."""
    own = p.get("colours") if isinstance(p.get("colours"), dict) else {}
    site = st.domain(p.get("website", ""))
    if not own and site:
        try:
            own = {k: v for k, v in (ks.look_from(settings, site) or {}).items() if k in COLOURS and v}
        except ValueError:  # no design system saved for their site
            own = {}
    return {**(base.get("colours") or palette(trade)), **{k: v for k, v in own.items() if k in COLOURS and v}}


def from_base(settings: Settings, name: str, p: dict, trade: str, args: dict):
    """(the lead's mock-up, the base's label) made from the trade's base design, or None when the trade has none.
    The trade of the week gets its base made the first time it's needed."""
    path = base_path(settings, trade)
    week = st.trade_of_week(settings)
    if not path.is_file():
        if week.get("trade") != trade:
            return None
        build_base(settings, trade)
    base = st.load(settings, f"kinetic-base-{trade}.json", {})
    services = [st.clean(x, 40) for x in (args.get("services") or []) if st.clean(x)] or ks.SERVICES[trade]
    html = personalise(path.read_text(encoding="utf-8"), name, st.clean(args.get("town") or p.get("town"), 40),
                       st.clean(args.get("phone") or p.get("phone"), 30), st.clean(p.get("address"), 160),
                       services, lead_colours(settings, p, trade, base), trade)
    label = week["label"] if week.get("trade") == trade else trade
    return st.write(settings, ("Mockups", name), "index.html", html, replace=True), label


def trade_of_week(settings: Settings, args: dict) -> str | screen.Shown:
    word = st.clean(args.get("trade"), 40).lower()
    week = st.trade_of_week(settings)
    if not word:
        if not week:
            return ("There's no trade of the week yet. Say \"this week is barbers\" (or cafes, plumbers, salons...) "
                    "and I'll focus the lead finder and outreach on it.")
        return (f"This week's trade is {week['label']} (set {st.short(tracker.day(week.get('set')))}). Lead "
                f"searches and outreach use it when you don't name a trade.")
    if word in CLEAR_WORDS:
        st.save(settings, st.TRADE_WEEK, {})
        return "Done: no trade of the week. Lead searches go back to all kinds of business."
    kind = kinetic_find.kind_key(word)
    if kind == "mixed":
        raise ValueError("Pick one trade for the week, e.g. barbers, cafes, plumbers or salons.")
    trade = ks.trade_of(word)
    trade = trade if trade != "business" else KIND_TRADES.get(kind, "business")
    st.save(settings, st.TRADE_WEEK, {"label": word, "kind": kind, "trade": trade, "set": st.today().isoformat()})
    path = base_path(settings, trade)
    fresh = args.get("rebuild") is True or bool(args.get("style_from")) or not path.is_file()
    if fresh:
        build_base(settings, trade, str(args.get("style_from") or "").strip())
    done = "I made its base mock-up design" if fresh else "Its base mock-up design is already made"
    return st.file_shown(settings, st.folder(settings, "Trade bases") / f"{trade} base preview.html",
                         f"This week is {word}. {done} ({st.where(settings, path)}): every {word.rstrip('s')} lead "
                         "gets their mock-up from it in seconds, with their name, colours, phone, address and "
                         "services swapped in. When you don't name a trade, I'll find and pitch "
                         f"{word}, anywhere in the world.", [
                             {"label": "Find leads", "say": f"Find {word} with weak websites near me."},
                             {"label": "Next outreach", "say": "Write outreach for the next lead of the week."}])


# ---- walk-in route ----------------------------------------------------------------------

def km(a: dict, b: dict) -> float:
    """Straight-line distance between two leads, in km."""
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(min(1.0, math.sqrt(h)))


def street_key(p: dict):
    """Sort key for a lead's address: street, then house number (so neighbours come together)."""
    first = str(p.get("address") or "").split(",")[0].strip().lower()
    m = re.match(r"^(\d+)\w*\s+(.*)$", first)
    return (m[2], int(m[1]), p["name"].lower()) if m else (first or "~", 0, p["name"].lower())


def has_spot(p: dict) -> bool:
    return isinstance(p.get("lat"), (int, float)) and isinstance(p.get("lon"), (int, float))


def route(stops: list[dict]) -> tuple[list[dict], bool]:
    """Walking order: nearest neighbour from the best lead when they have map positions, else by street."""
    placed = [p for p in stops if has_spot(p)]
    if len(placed) < 2:
        return sorted(stops, key=street_key), False
    order, left = [placed[0]], placed[1:]
    while left:
        nxt = min(left, key=lambda p: km(order[-1], p))
        order.append(nxt)
        left.remove(nxt)
    return order + sorted([p for p in stops if not has_spot(p)], key=street_key), True


def walk_in_script(settings: Settings, p: dict) -> str:
    me = st.business(settings)
    hook = kinetic_find.biggest_problem(p).get("line", "")
    return (f"Go in at a quiet time (mid-morning or mid-afternoon) with their mock-up open on your phone. \"Hi, I'm "
            f"from {me['name']}, a web designer just round the corner. {hook} So I made you this: a free example of "
            f"a new home page for {p['name']}. Can I show you in 30 seconds? {st.PREVIEW}\" If they like it, ask "
            "for the best WhatsApp or email to send it to; if they ask about price, it's "
            f"{world.payment_terms(ks.prices(settings)['deposit_percent'])}. If they're busy, ask when's better, and "
            "if they say no, thank them and don't come back.")


def walk_in_route(settings: Settings, args: dict) -> screen.Shown:
    town = st.need(args.get("town"), "town", 80)
    week = st.trade_of_week(settings)
    asked = st.clean(args.get("trade"), 40)
    trade = ks.trade_of(asked) if asked else week.get("trade", "")
    if asked and trade == "business":
        trade = KIND_TRADES.get(kinetic_find.kind_key(asked), "business")
    label = asked or week.get("label", "")
    status = {r.get("prospect"): r.get("status") for r in tracker.all_leads(settings) if r.get("prospect")}
    key = town.lower()
    pool = [p for p in st.rows_of(settings, st.PROSPECTS)
            if key in f"{p.get('town', '')} {p.get('address', '')}".lower()
            and (not p.get("website") or kinetic_find.social_only(p))
            and status.get(p.get("id"), "new") in ("new", "drafted")]
    picked = [p for p in pool if not trade or ks.trade_of(f"{p.get('kind', '')} {p['name']}") == trade]
    note = ""
    if trade and not picked and pool:
        picked, note = pool, f" None of them are {label}, so the route has every trade."
    if not picked:
        raise ValueError(f"I haven't got any uncontacted leads with no website in {town}"
                         + (f" for {label}" if label else "") + ". Ask me to find some there first.")
    picked = sorted(picked, key=kinetic_find.rank_key)[:max(1, min(int(args.get("count") or ROUTE_STOPS), ROUTE_STOPS))]
    order, mapped = route(picked)
    lines = [f"# Walk-in route: {town}" + (f" ({label})" if label and not note else ""), "",
             f"Planned by Alfred on {st.long_date(st.today())}. {len(order)} businesses with no website, "
             + ("in walking order (nearest next)." if mapped else "sorted by street, as I don't have map positions.")
             + " Every stop's mock-up is saved in Kinetic Web Designs/Mockups.", ""]
    rows, total, prev = [], 0.0, None
    for n, p in enumerate(order, 1):
        ks.outreach_mockup(settings, {"client": str(p["id"])})  # fast from the trade's base when there is one
        step = km(prev, p) if prev and has_spot(prev) and has_spot(p) else None
        total += step or 0
        prev = p
        problem = kinetic_find.biggest_problem(p).get("label", "no website")
        lines += [f"## {n}. {p['name']}", "", f"{p.get('address') or 'No address saved'}"
                  + (f" · {step:.1f} km from the last stop" if step is not None else "")
                  + (f" · {p['phone']}" if p.get("phone") else ""), "", walk_in_script(settings, p), ""]
        rows.append([str(n), p["name"], p.get("address") or "-", problem, f"{step:.1f} km" if step is not None else "-"])
        tracker.drafted(settings, p["name"], p, "visit", p.get("country", ""), mockup=True)
    if mapped:
        spots = "/".join(f"{p['lat']},{p['lon']}" for p in order if has_spot(p))
        lines += [f"Walking directions: https://www.google.com/maps/dir/{spots}", ""]
    lines += ["Walk-ins suit every country's rules for cold contact. Be friendly, keep it to 30 seconds, and take no "
              "for an answer. Tell me who you visited (\"I visited Sal's Cafe\") and I'll note it.", ""]
    path = st.write(settings, ("Walk-in routes",), f"{town} walk-in route {st.today().isoformat()}.md",
                    "\n".join(lines), replace=True)
    walk = f", about {total:.1f} km in all" if mapped and total else ""
    text = (f"Your walk-in route in {town}: {len(order)} stop{'s' if len(order) != 1 else ''}{walk}, starting at "
            f"{order[0]['name']}.{note} Each has a 30-second script and its mock-up ready on your phone. "
            f"Saved in {st.where(settings, path)}. {st.NOT_SENT}")
    return st.table(text, f"Walk-in route: {town}", ["#", "Business", "Address", "Problem", "Walk"], rows)


# ---- the mock-up video on its own ------------------------------------------------------------

async def video(settings: Settings, args: dict) -> str | screen.Shown:
    name, prospect = ks.client_and_prospect(settings, args)
    html = st.folder(settings, "Mockups", name) / "index.html"
    if not html.is_file():
        ks.outreach_mockup(settings, {k: v for k, v in args.items() if k in ("client", "business")})
    hook = kinetic_find.biggest_problem({**(prospect or {}), "name": name}).get("line", "")
    path, why = await kinetic_video.make(settings, name, hook, html)
    if not path:
        return why
    return st.file_shown(settings, path, f"I made {name}'s 30-second mock-up video (1080 by 1920, for phones): "
                         f"{st.where(settings, path)}. Attach it to their message yourself. {why}".strip())


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_design_reach",
        "description": "Kinetic Web Designs reach. trade_of_week: set the trade of the week (\"this week is "
                       "barbers\", trade) or say what it is (no trade; trade 'none' clears it). The client finder and "
                       "outreach use it when no trade or lead is named, worldwide, and it builds ONE base mock-up "
                       "design for the trade that every lead of that trade reuses with their own name, colours, phone, "
                       "address and services (rebuild true or style_from to remake it). walk_in_route: up to 10 "
                       "uncontacted no-website leads in a town (trade of the week unless trade is given) in walking "
                       "order, each with a one-paragraph walk-in script and its mock-up. video: a 30-second vertical "
                       "video of a lead's mock-up scrolling on a phone with a short voice-over, to attach to their "
                       "message. Never sends anything.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "trade": {"type": "string", "description": "trade_of_week: the trade, e.g. barbers, cafes, plumbers, "
                                                           "salons, or 'none'. walk_in_route: a trade other than the "
                                                           "week's."},
                "rebuild": {"type": "boolean", "description": "trade_of_week: make the trade's base design again."},
                "style_from": {"type": "string", "description": "trade_of_week: base the design on a design system "
                                                                "saved by extract_design_system, e.g. 'stripe.com'."},
                "town": {"type": "string", "description": "walk_in_route: the town or area."},
                "count": {"type": "integer", "description": "walk_in_route: stops, up to 10 (default 10)."},
                "client": {"type": "string", "description": "video: a saved prospect's number or name."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    if args.get("action") == "video":
        return await video(settings, args)
    return await asyncio.to_thread(st.dispatch, {"trade_of_week": trade_of_week, "walk_in_route": walk_in_route},
                                   args.get("action"), settings, args, "reach")
