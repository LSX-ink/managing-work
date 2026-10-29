"""The outbox: first emails and email follow-ups that go out on their own, once Vera (quality control) passes them.

The owner asked for this (21 Oct 2026): emails shouldn't wait for their approval; an 8th agent double-checks every
email before it goes. DMs and WhatsApp still go by hand (Instagram doesn't allow apps to message first).

Guard rails, all enforced here, before anything is sent:
- only where a cold email is allowed: kinetic_world.cold_email_ok (UK PECR: limited companies only; never in the
  countries where cold email needs consent)
- never to anyone opted out, not interested, already talking to us, or already emailed today
- settings.send_per_day emails a day (default 15): one per run, more when behind the day's pace so the limit is
  always reached; leads with no email don't count; only Monday to Saturday 09:00 to 17:30 UK
- every email: the business's real problem, the free mock-up as a link, "See your design before you pay anything",
  half when we start building and half once complete, signed Alfred, an opt-out line, no placeholders, no Klarna
- then the free AI reads it as a strict editor and must answer APPROVE
- replies are watched: an opt-out ("no thanks", "unsubscribe", "stop") marks them opted out for good; any other
  reply marks them replied (no more follow-ups) and puts them on the owner's list
Sent emails go from Alfred's own address and are recorded in the outreach tracker, so follow-ups come at days 3, 7, 14
and 21 (four, then stop; a reply or a no stops them sooner).
"""

import asyncio
import email.utils
import json
import math
import re
import subprocess
from datetime import datetime
from pathlib import Path

import alfred_mail
import kinetic_find as kf
import kinetic_outreach as tracker
import kinetic_sales as sales
import kinetic_store as st
import kinetic_world as world
from hq import mockup

SITE = "https://kineticwebdesigns.co.uk"
LIVE = Path(r"C:\Users\Thato\kinetic-repo\kinetic-live")
OPT_OUT_WORDS = re.compile(r"\b(no thanks|no thank you|unsubscribe|stop|remove me|not interested|don'?t contact)\b", re.I)
BAD_ADDRESS = re.compile(r"^(no-?reply|donotreply|do-not-reply|mailer-daemon|postmaster|abuse|privacy|gdpr)@|"
                         r"\.(png|jpe?g|gif|webp|svg)$|example\.(com|org)|sentry|wixpress|godaddy", re.I)
MUST = [
    ("See your design before you pay anything", "the 'see your design before you pay anything' line"),
    ("Alfred", "Alfred's signature"),
    ("reply 'no thanks'", "the opt-out line"),
]
NEVER = [(re.compile(r"klarna|monthly payments?|pay monthly", re.I), "Klarna or monthly-payment wording"),
         (re.compile(r"\[[^\]]{2,40}\]"), "a [placeholder] left in"),
         (re.compile(r"thato|lesufi", re.I), "the owner's personal name"),
         (re.compile(r"\bit'?s attached\b|enclosed", re.I), "a claim that something is attached")]


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48] or "your-business"


def uk_now() -> datetime:
    return datetime.now()  # the PC runs on UK time


def in_hours(now: datetime) -> bool:
    return now.weekday() < 6 and (9, 0) <= (now.hour, now.minute) <= (17, 30)


def on_pace(cap: int, now: datetime) -> int:
    """How many emails should be out by now for the day's cap to be reached by 17:00, spread evenly from 9:00."""
    done = (now.hour * 60 + now.minute - 9 * 60) / (8 * 60)
    return max(1, math.ceil(cap * min(1.0, max(0.0, done))))


# ---- finding who to email ------------------------------------------------------------------------

def good_address(addr: str, website: str = "") -> bool:
    return bool(addr and alfred_mail.EMAIL_ADDR.match(addr) and not BAD_ADDRESS.search(addr))


def pick_address(emails: list[str], website: str) -> str:
    host = re.sub(r"^https?://(www\.)?", "", website or "").split("/")[0].lower()
    ok = [e.strip().lower() for e in emails if good_address(e.strip())]
    same = [e for e in ok if host and e.split("@")[1].endswith(host)]
    return (same or ok or [""])[0]


def closed_or_busy(row: dict | None) -> bool:
    return bool(row) and row.get("status") not in ("new", "drafted")


MIN_REVIEWS = 25    # fewer reviews than this: too small or too quiet to be making real money
MIN_RATING = 3.8    # customers like them: they're worth helping, and they'll care about how they look online


def busy_score(p: dict) -> float:
    """How likely this business is open, busy and making money, from what Google shows: lots of reviews (customers
    keep coming), a good rating, and (once Vera has read their site) online booking that people use. 0 = skip."""
    reviews, rating = int(p.get("reviews") or 0), float(p.get("rating") or 0)
    if reviews < MIN_REVIEWS or rating < MIN_RATING or str(p.get("status") or "").lower() in ("closed", "dead"):
        return 0.0
    score = min(reviews, 1500) ** 0.5 * 2 + (rating - 3.5) * 10
    if p.get("_booking"):
        score += 15  # takes bookings online: a real, active business
    return score


def _fresh_busy(settings) -> list[dict]:
    """Busy leads we haven't messaged yet, best first."""
    by_name = {r["name"].lower(): r for r in st.rows_of(settings, st.OUTREACH)}
    out = [p for p in st.rows_of(settings, st.PROSPECTS)
           if not closed_or_busy(by_name.get(p["name"].lower())) and busy_score(p) > 0
           and (by_name.get(p["name"].lower()) or {}).get("draft_channel") != "dm"]  # on the owner's DM list already
    return mix_trades(sorted(out, key=busy_score, reverse=True))


def mix_trades(rows: list[dict]) -> list[dict]:
    """Best first within each trade, taking turns between trades (owner, 29 Oct 2026: "just trade mix", for the DMs
    and the emails), so a day's list isn't all barbers."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(trade_group(r), []).append(r)
    out, lists = [], list(groups.values())
    while lists:
        out += [g.pop(0) for g in lists]
        lists = [g for g in lists if g]
    return out


def trade_group(p: dict) -> str:
    k = str(p.get("kind") or "").lower()
    if "barber" in k:
        return "barber"
    if "hair" in k:
        return "hair"
    if re.search(r"beauty|nail|lash|brow|spa|skin|tann|makeup|massage", k):
        return "beauty"
    for word, group in (("restaurant", "restaurant"), ("cafe", "cafe"), ("coffee", "cafe"), ("gym", "fitness"),
                        ("fitness", "fitness"), ("garage", "garage"), ("car ", "garage"), ("auto", "garage"),
                        ("mechanic", "garage"), ("clinic", "health"), ("dent", "health"), ("physio", "health")):
        if word in k + " ":
            return group
    return k or "other"


def candidates(settings, ltd: set | None = None) -> list[dict]:
    """Fresh, busy, money-making leads with a website where a cold email is allowed: most likely to reply first.
    Quiet businesses (few reviews, low rating) are left out entirely. ltd: UK leads Companies House shows are
    limited companies (PECR allows a cold email to them even when the name doesn't say Ltd)."""
    out = []
    for p in _fresh_busy(settings):
        if not p.get("website") or kf.social_only(p):
            continue
        country = p.get("country") or world.HOME
        if not (world.cold_email_ok(country, p["name"]) or (ltd and p["id"] in ltd)):
            continue
        out.append(p)
    return out


def is_uk(p: dict) -> bool:
    return world.rules_of(p.get("country") or world.HOME) == "uk"


def sole_traders(settings, ltd: set) -> list[dict]:
    """Busy leads we can't cold-email (UK sole traders and partnerships under PECR, and countries where a sales
    email needs consent first): the owner DMs these by hand."""
    return [p for p in _fresh_busy(settings) if not world.cold_email_ok(p.get("country") or world.HOME, p["name"])
            and p["id"] not in ltd]


# ---- Companies House: is a UK lead a limited company? -------------------------------------------------

CH = "https://find-and-update.company-information.service.gov.uk"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kinetic Web Designs lead check"}
CH_ITEM = re.compile(r'<li class="type-company">.*?href="/company/(\w+)".*?>\s*(.*?)\s*</a>.*?'
                     r'<p class="meta crumbtrail">(.*?)</p>\s*<p>(.*?)</p>', re.S)


def _norm(name: str) -> str:
    name = re.sub(r"\b(limited|ltd|the|uk)\b", " ", name.lower().replace("&", " and "))
    return re.sub(r"[^a-z0-9]+", "", name)


def _outcode(text: str) -> str:
    m = re.search(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*\d[A-Z]{2}\b", text.upper())
    return m.group(1) if m else ""


def _base_name(p: dict) -> str:
    """The trading name without a branch or town tag: "Ted's Grooming Room | Soho" -> "Ted's Grooming Room"."""
    name = re.split(r"\s+[|\-–]\s+|\s*\|\s*", p["name"])[0]
    town = str(p.get("town") or "").strip()
    if town and name.lower().endswith(" " + town.lower()):
        name = name[: -len(town) - 1]
    return name.strip()


async def companies_house(http, p: dict) -> str:
    """The company number when Companies House lists an active limited company with this exact name in the same
    town or postcode area; "" otherwise. Strict on purpose: when in doubt it counts as a sole trader (no email)."""
    name = _base_name(p)
    for attempt in range(3):  # the public search often answers 502 when busy
        r = await http.get(f"{CH}/search", params={"q": name}, headers=UA, timeout=25)
        if r.status_code != 502:
            break
        await asyncio.sleep(4 * (attempt + 1))
    r.raise_for_status()
    town, area = str(p.get("town") or "").lower(), _outcode(p.get("address") or "")
    for number, title, meta, address in CH_ITEM.findall(r.text):
        if "dissolved" in meta.lower() or _norm(title) != _norm(name) or not re.search(r"\b(limited|ltd)\b", title, re.I):
            continue
        if (town and town in address.lower()) or (area and _outcode(address) == area):
            return number
    return ""


async def check_companies(ctx, limit: int = 8) -> int:
    """Look up the next few busy UK leads with a website on Companies House (cached in the brain as ch.<id>)."""
    b, done = ctx.brain, 0
    for p in _fresh_busy(ctx.settings):
        if done >= limit:
            break
        if not is_uk(p) or not p.get("website") or world.cold_email_ok(world.HOME, p["name"]) or \
                b.get(f"ch.{p['id']}") is not None:
            continue
        try:
            number = await companies_house(ctx.http, p)
        except Exception:
            break  # Companies House is busy or down: try again next run
        b.set(f"ch.{p['id']}", number)
        if number:
            b.log("warden", f"{p['name']} is a limited company (Companies House {number}), so it can be emailed", "info")
        done += 1
        await asyncio.sleep(3)
    return done


def limited_companies(brain) -> set:
    return {int(k[3:]) for k, v in brain.facts().items() if k.startswith("ch.") and v and k[3:].isdigit()}


async def email_for(ctx, p: dict) -> str:
    """The lead's email: from the listing, else read off their website (cached in the brain)."""
    b = ctx.brain
    key = f"email.{p['id']}"
    known = b.get(key)
    if known is not None:
        return known
    addr = p.get("email") if good_address(p.get("email") or "") else ""
    if not addr and p.get("website"):
        try:
            audit = await asyncio.wait_for(kf.audit_url(ctx.http, p["website"]), 45)
            if audit.get("grade") == "down":
                b.set(key, "")  # a dead site: not a business we email
                return ""
            addr = pick_address(audit.get("emails") or [], p["website"])
            b.set(f"booking.{p['id']}", bool(audit.get("booking")))
        except Exception:
            addr = ""
    b.set(key, addr)
    return addr


# ---- the mock-up, online -------------------------------------------------------------------------

def publish_mockup(settings, p: dict, deploy: bool = True) -> str:
    """Make the lead's mock-up and put it online at kineticwebdesigns.co.uk/m/<name>/ (hidden from Google).
    deploy=False only writes it into the site, for a batch that deploys once at the end (deploy_site)."""
    if mockup.trade_for(p) != "business" or not sales.store_lead(p):  # the premium concept (23 Oct 2026)
        html = mockup.html_for(p, st.business(settings)["name"])
        st.write(settings, ("Mockups", p["name"]), "index.html", html, replace=True)
    else:  # Shopify stores keep their store makeover
        sales.outreach_mockup(settings, {"client": p["id"]})
        html = (st.folder(settings, "Mockups", p["name"]) / "index.html").read_text(encoding="utf-8")
    if "noindex" not in html:
        html = html.replace("<head>", '<head><meta name="robots" content="noindex, nofollow">', 1)
    out = LIVE / "m" / slug(p["name"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    if deploy:
        deploy_site()
    return f"{SITE}/m/{slug(p['name'])}/"


async def make_mockup(ctx, p: dict) -> str:
    """Iris (hq/designer.py) builds and checks the lead's mock-up in the site folder; its link, or "" when it was held
    back. Call deploy_site() afterwards to put it online. Shopify stores keep their store makeover."""
    from hq import designer
    if mockup.trade_for(p) == "business" and sales.store_lead(p):
        return await asyncio.to_thread(publish_mockup, ctx.settings, p, False)
    if ctx.brain.get("settings.premium_mockups", True):  # owner, 27-28 Oct 2026: every mock-up uses all the skills
        return await premium_mockup(ctx, p)
    ok, _ = await designer.build(ctx, p, LIVE / "m" / slug(p["name"]), st.business(ctx.settings)["name"])
    if ok:
        ctx.brain.set(f"iris.{p['id']}", mockup.VERSION)
    return f"{SITE}/m/{slug(p['name'])}/" if ok else ""


async def premium_mockup(ctx, p: dict) -> str:
    """The premium designer (hq/premium/auto.py) for the morning list: research, every design skill and the website kit,
    the design review, 3D, before/after, online and checked. Its link, or "" when a check failed. A lead whose own site
    already rates well is marked strong_site, as Iris did, so Blade puts them last."""
    import sys
    import omniroute
    sys.path.insert(0, str(Path(__file__).parent / "premium"))
    import auto
    r = await auto.make(f"{p['name']}, {p.get('town') or p.get('address') or ''}".strip(", "), ctx.settings,
                        omniroute.make_client(ctx.settings), p.get("website") or "", (p.get("instagram") or "").lstrip("@"))
    if (r.get("audit") or {}).get("grade") == "good":
        ctx.brain.set(f"strong_site.{p['id']}", True)
    if r["issues"]:
        ctx.brain.log("closer", f"{p['name']}: mock-up held back, checks found {'; '.join(r['issues'][:3])}", "warn")
        return ""
    return r["link"]


def deploy_site() -> None:
    r = subprocess.run(["npx.cmd", "--yes", "wrangler", "pages", "deploy", ".", "--cwd", str(LIVE), "--project-name",
                        "kinetic", "--branch", "main", "--commit-dirty=true"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=300)
    if r.returncode != 0:
        raise RuntimeError("couldn't put the mock-up online: " + (r.stderr or r.stdout)[-200:])


IG_LINK = re.compile(r"instagram\.com/([A-Za-z0-9_.]{2,30})", re.I)
IG_NOT_A_NAME = {"p", "reel", "reels", "explore", "accounts", "stories", "tv", "about", "developer", "legal",
                 "sharer", "share", "invites", "direct", "web", "embed"}


def same_business(title: str, handle: str, name: str) -> bool:
    """The profile belongs to the business: its display name or @handle shares a real word with the business's name.
    Owner, 28 Oct 2026: Fade Inn Salon's website linked a staff member's own account (@gabi_6987), not @fade_inn_salon."""
    stop = {"the", "and", "barber", "barbers", "barbershop", "shop", "salon", "hair", "beauty", "studio", "of", "ltd", "co"}
    words = {w for w in re.findall(r"[a-z0-9]+", name.lower()) if len(w) > 2 and w not in stop}
    seen = re.sub(r"[^a-z0-9]+", " ", f"{title} {handle}".lower())
    squashed = seen.replace(" ", "")
    return not words or any(w in seen.split() or w in squashed for w in words)


async def instagram_exists(handle: str, name: str = "") -> bool:
    """True only when instagram.com/<handle> is a real, live profile (owner, 26 Oct 2026: a dead @name went on the DM
    list; "you should have checked this before sending it to me"). Logged-out Instagram says "Profile isn't available"
    for names that don't exist; a real one shows "<Name> (@handle)" in the title. With the business's name, the profile
    must also be theirs (same_business), not someone else's account their website happens to link."""
    from playwright.async_api import async_playwright
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(channel="msedge")
            pg = await (await b.new_context(locale="en-GB")).new_page()
            await pg.goto(f"https://www.instagram.com/{handle.strip('@')}/", wait_until="domcontentloaded", timeout=30000)
            await pg.wait_for_timeout(3000)
            title = await pg.title()
            await b.close()
        live = f"(@{handle.strip('@').lower()})" in title.lower()
        return live and (not name or same_business(title, handle, name))
    except Exception:
        return False


async def instagram_handle(http, p: dict) -> str:
    """The business's Instagram name, read off the Instagram link on their website ("" when there isn't one)."""
    site = p.get("website") or ""
    if not site:
        return ""
    for url in (site, site.rstrip("/") + "/contact", site.rstrip("/") + "/contact-us"):
        try:
            r = await http.get(url, headers=UA, timeout=20)
        except Exception:
            continue
        names = [h.rstrip(".") for h in IG_LINK.findall(r.text) if h.lower() not in IG_NOT_A_NAME]
        if names:
            return names[0]
    return ""


PLAIN = [  # our audit's short labels, said the way a shop owner would understand them
    (r"tap", "customers can't tap your number to ring you from their phone"),
    (r"google can't read|business details|structured", "Google can't read your business details, so you show up less in searches"),
    (r"title|description|meta", "it doesn't tell Google what you do, so you show up less in searches"),
    (r"share preview|preview", "your link shows no preview picture when it's shared on WhatsApp or Instagram"),
    (r"slow|speed", "your site is slow to open on phones"),
    (r"secure|https", "browsers warn people your site isn't secure"),
    (r"book", "there's no easy way to book online"),
]


def plain(problem: str) -> str:
    for pattern, said in PLAIN:
        if re.search(pattern, problem, re.I):
            return said
    text = re.sub(r"\bgoogle\b", "Google", problem.strip().rstrip("."))
    return text[0].lower() + text[1:] if text[:1].isupper() and not text.startswith("Google") else text


BUSY = 150  # Google reviews: past this a shop is usually fully booked, so "more customers" isn't the pitch


STAY = re.compile(r"guest ?house|lodge|villa|\bstay|apartment|b&b|bed and breakfast|cottage|self.catering|airbnb|holiday|retreat|"
                  r"wine estate|wine farm|safari|game reserve|boutique hotel|manor house", re.I)


def stay(p: dict) -> bool:
    """A short-let host (guesthouse, lodge, villa, Airbnb): their pitch is direct bookings, not more customers."""
    return bool(STAY.search(f"{p.get('kind', '')} {p.get('name', '')}"))


def busy(p: dict) -> bool:
    return int(p.get("reviews") or 0) >= BUSY and float(p.get("rating") or 0) >= 4.6


def praise_and_gap(p: dict, brain=None) -> tuple[str, str]:
    """About them first (their real Google rating), then their one biggest website problem, said plainly. A busy,
    well-rated shop hears what a site saves them (no-shows, phone time, cheap prices) instead of "more customers":
    Exposure Men Studio replied "fully booked, no need" to the old pitch (24 Oct 2026)."""
    rating, reviews = p.get("rating"), int(p.get("reviews") or 0)
    praise = (f"{float(rating):.1f}★ from {reviews:,} Google reviews is seriously impressive, your customers clearly "
              "love you." if rating and reviews >= 25 else "your customers clearly rate you.")
    extra = (brain.get(f"design.{p['id']}") if brain else None) or {}  # what Iris found on their site
    speed = extra.get("speed")
    found = [a for a, _ in extra.get("fixes") or [] if p.get("website")]
    problem = kf.biggest_problem({**p, "name": p["name"]}).get("short") or ""
    problem = re.sub(r"^I had a look at your website \(([^)]+)\):\s*", r"on \1, ", problem.strip())
    problem = re.sub(r"\bgoogle\b", "Google", problem)
    if found and not problem:
        problem = f"on your website, {plain(found[0])}"
    if problem and not problem.endswith("."):
        problem += "."
    if problem.startswith("Your "):
        problem = "y" + problem[1:]
    if isinstance(speed, int) and speed < 50:
        problem = (problem + " " if problem else "") + f"Google also scores your site just {speed}/100 for speed on phones."
    if stay(p) and p.get("website") and not re.search(r"airbnb|booking\.com|facebook|instagram", p["website"], re.I):
        # they already have a site (owner, 25 Oct 2026: show the before and after): sell the upgrade, not "get a website"
        gap = ("A lot of your guests probably still book through Booking.com and the like, and they take a big cut of "
               "every stay. Your website is the one place guests book you directly, so it should sell the stay as well "
               "as you do: every room, the views and the real layout, synced with your calendars.")
        if problem:
            gap = f"One thing I spotted: {problem} " + gap
    elif stay(p):
        gap = ("Right now most of your guests probably book through Airbnb or Booking.com, and they take a big cut of "
               "every stay. Your own website, synced with those calendars, lets guests book you directly, see every "
               "room before they choose, and come back without the middleman.")
        if problem:
            gap = f"One thing I spotted: {problem} " + gap
    elif busy(p):
        gap = ("A business this busy doesn't need more walk-ins. What a great website does for you is take bookings "
               "and deposits while you're cutting, so no-shows stop costing you and the phone stops interrupting, "
               "and it lets your work and reviews justify premium prices.")
        if problem:
            gap = f"One thing I spotted: {problem} " + gap
    else:
        gap = (f"One thing I spotted: {problem}" if problem else
               ("Your website doesn't show off how good you are yet." if p.get("website") else
                "You don't have a website yet, so people who find you on Google can't see your work or book easily."))
    return praise, gap


def dm_text(settings, p: dict, link: str, brain=None) -> str:
    """The Instagram DM the owner sends by hand. Short (owner, 26 Oct 2026: "the message as an integrity can't be long"):
    their rating, the concept in their own colours, that it's only a mock-up, our website, an easy reply. Stays also say
    the model and drone flight are representative and more photos make it exactly their place."""
    name = _base_name(p)
    rating, reviews = p.get("rating"), int(p.get("reviews") or 0)
    hello = (f"{float(rating):.1f}★ from {reviews:,} Google reviews, that's seriously impressive. " if rating and reviews >= 25 else "")
    if stay(p):
        made = (f"We made you a free concept website from your own photos and reviews (the model and drone flight are "
                f"representative):\n{link}\n\nIt's only a mock-up. Send us more photos and we'll make it exactly your place, "
                "even better. Our work: kineticwebdesigns.co.uk")
    else:
        made = (f"We made you a free concept website in your own colours, with your own photos and reviews:\n{link}\n\n"
                "It's only a quick mock-up. Have a look at kineticwebdesigns.co.uk and we'll have your full site looking like that.")
    # yes or no, ask for a follow (owner, 26 Oct 2026: "so that if they change their mind they can always come back")
    return (f"Hi {name} team \U0001F44B\n\n{hello}{made}\n\nInterested? Just reply here and give us a follow so we can stay in "
            "touch. Not for you right now? No problem at all, give us a follow anyway, so you can always come back if you "
            "change your mind.\n\nKinetic Web Designs")


def dm_text_long(settings, p: dict, link: str, brain=None) -> str:
    """The older long DM (kept for reference; owner asked for short ones on 26 Oct 2026): warm, about
    them first, their one biggest website problem, then the mock-up made from their own photos and reviews, the
    no-risk terms, and an easy way to say no."""
    name = _base_name(p)
    praise, gap = praise_and_gap(p, brain)
    return (f"Hi {name} team! \U0001F44B\n\nI came across you on Google, and {praise}\n\n{gap} So I put together a free "
            f"concept of what your website could look like, using your own photos and reviews:\n{link}\n\n"
            + ("Your current homepage and the new design are side by side on the page, so you can compare.\n\n"
               if stay(p) and (Path(LIVE) / "m" / link.rstrip("/").rsplit("/", 1)[-1] / "before.jpg").exists() else "")
            # owner, 26 Oct 2026: say the concept uses representative imagery, and more photos make it exactly their place
            + ("We built it from the photos you already have online, plus some representative imagery (like the model "
               "and the drone fly-in) to show what's possible. If you send us more photos of your place, we'll make the "
               "site look exactly like it, and even better, all done professionally.\n\n" if stay(p) else "")
            + "It's yours to look at, no catch. If you love it, we can make it real, and you only pay half when we "
            "start and half once it's finished.\n\nWould love to hear what you think!\nKinetic Web Designs\n\n"
            "(If it's not for you, just say and I won't message again.)")


def dm_text_short(settings, p: dict, link: str) -> str:
    """The older, shorter DM (kept for reference): Alfred's first message with the mock-up as a link."""
    body = sales.outreach_draft(settings, {"client": p["id"]}, "dm")["body"]
    body = re.sub(r" \([^()]*mock-up[^()]*\.html\)", "", body)
    body = re.sub(r"\bgoogle\b", "Google", body).replace(p["name"], _base_name(p))  # "Ted's Grooming Room", not "... | Soho"
    return re.sub(r"(a free (?:home page|store makeover) mock-up)", rf"\1: {link}", body, count=1) \
        if link not in body else body


# ---- writing ----------------------------------------------------------------------------------------

def split_subject(body: str) -> tuple[str, str]:
    m = re.match(r"Subject: (.+?)\n\n", body)
    return (m.group(1).strip(), body[m.end():]) if m else ("", body)


def first_email(settings, p: dict, link: str, brain=None) -> tuple[str, str]:
    """Vera's first email, written like the DM: about them first, their one problem (or, for a busy shop, what a
    site saves them), the free concept link, the price and terms, then an easy yes. Price, sign-off, contact
    details and opt-out come from the sales draft, so the country rules still apply."""
    d = sales.outreach_draft(settings, {"client": p["id"]}, "email")
    _, old = split_subject(d["body"])
    name = _base_name(p)
    praise, gap = praise_and_gap(p, brain)
    price = re.search(r"(Websites start from [^\n]+?\.|A Shopify store redesign is [^\n]+)", old)
    tail = old[old.index("Thanks,"):] if "Thanks," in old else ""
    rating, reviews = p.get("rating"), int(p.get("reviews") or 0)
    subject = (f"A free website idea for {name} ({float(rating):.1f}★ on Google)" if rating and reviews >= 25
               else f"A free website idea for {name}")
    ask = ("Would it help if I showed you how online booking with deposits would work for you? Just reply 'yes' "
           "and I'll send it over." if busy(p) else
           "Just reply 'yes' if you'd like to talk it through, it only takes 10 minutes.")
    body = (f"Hi {name} team,\n\nI came across you on Google, and {praise}\n\n{gap}\n\n"
            "So I put together a free concept of what your website could look like, using your own photos and "
            f"reviews. You can open it on your phone here: {link}\n\n{st.PREVIEW}\n\n"
            + (f"If you like it, {price.group(1)[0].lower() + price.group(1)[1:]} If not, no problem at all.\n\n" if price else "")
            + f"{ask}\n\n{tail}")
    return subject, body


def follow_up_email(settings, name: str, link: str, updated: bool = False) -> tuple[str, str] | None:
    """updated: the link is a fresh mock-up made with the new designer, so the email says so (owner, 29 Oct 2026)."""
    d = tracker.follow_up_draft(settings, {"business": name, "channel": "email"})
    if d.get("stop"):
        return None
    subject, body = split_subject(d["body"])
    if link and updated:
        parts = body.split("\n\n")
        parts.insert(2, f"Since my last email I've made you a new, updated design for {name}, free and with no "
                        f"obligation: {link}")
        body = "\n\n".join(parts)
    elif link:
        body = body.replace("is still yours to see, with no obligation.", f"is still yours to see, with no obligation: {link}")
    return subject, body


async def refresh_mockup(ctx, row: dict) -> str:
    """A follow-up's lead gets one new mock-up from the premium designer (a new -v2 link; the sent one never changes),
    made only when their follow-up is about to go, so credit is spent on emails that are sent. "" when it can't."""
    b = ctx.brain
    key = f"mockup_updated.{row['name'].lower()}"
    if b.get(key):
        return b.get(key)
    p = st.find_prospect(st.rows_of(ctx.settings, st.PROSPECTS), row.get("prospect") or row["name"]) or {}
    p = {**p, "name": row["name"]}
    link = await premium_mockup(ctx, p)
    if link:
        b.set(key, link)
    return link


# ---- Vera's checks ----------------------------------------------------------------------------------

def rule_check(subject: str, body: str, link: str, first: bool) -> list[str]:
    problems = [why for text, why in MUST if text.lower() not in body.lower()]
    problems += [why for rx, why in NEVER if rx.search(body) or rx.search(subject)]
    if first and link and link not in body:
        problems.append("the mock-up link is missing")
    if "half" not in body.lower() and first:
        problems.append("the payment terms (half when we start, half once complete)")
    if not subject or len(subject) > 120:
        problems.append("a missing or overlong subject")
    if len(body) > 3000:
        problems.append("it's too long")
    return problems


async def ai_check(ctx, p: dict, subject: str, body: str) -> tuple[bool, str]:
    prompt = ("You are Vera, the strict quality-control editor at Kinetic Web Designs, a UK web design agency. "
              "Check this cold email before it is sent to a real small business. Approve only if ALL are true: "
              "it is addressed to the right business; every claim about their website is plausible from the facts; "
              "it is polite, professional, honest and specific; British English; no made-up facts, prices or "
              "promises beyond: websites from £395 (or the local equivalent), half when we start building and half "
              "once complete, a free home page mock-up, 'see your design before you pay anything'; it is signed by "
              "Alfred; it has an opt-out line. A price in the business's own currency (e.g. $499 or €459) is the "
              "local equivalent of £395 and is fine. For a follow-up, the date of our first email is in the facts "
              "(first_email_sent) and is real, and when made_them_an_updated_mockup is true the new design and its link are real. Reply with ONLY JSON: {\"approve\": true|false, \"reason\": \"...\"}.\n\n"
              f"Business facts: {json.dumps({k: p.get(k) for k in ('name', 'kind', 'town', 'country', 'website', 'rating', 'reviews', 'first_email_sent', 'messages_so_far', 'made_them_an_updated_mockup') if p.get(k) not in (None, '')})}\n\n"
              f"Subject: {subject}\n\n{body}")
    try:
        text = await ctx.ask_ai(prompt, 2500)
        m = re.search(r"\{.*\}", text, re.S)
        try:
            verdict = json.loads(m.group(0)) if m else {}
        except ValueError:
            verdict = {}
        if "approve" not in verdict:  # a cut-off or fenced answer: read the verdict itself
            flag = re.search(r'"approve"\s*:\s*(true|false)', text, re.I)
            why = re.search(r'"reason"\s*:\s*"([^"]*)', text)
            verdict = {"approve": bool(flag and flag.group(1).lower() == "true"), "reason": why.group(1) if why else text[:200]}
        return bool(verdict.get("approve")), str(verdict.get("reason") or text[:200])
    except Exception as e:
        return False, f"the AI check couldn't run ({type(e).__name__}), so it waits"


# ---- sending and recording --------------------------------------------------------------------------

def send(settings, to: str, subject: str, body: str) -> str:
    alfred_mail.draft(settings, {"to": to, "subject": subject, "body": body})
    rows = alfred_mail._load_drafts(settings)
    d = max((r for r in rows if r.get("status") == "draft" and r.get("to") == to), key=lambda r: r["id"])
    return alfred_mail.send(settings, {"draft_id": d["id"], "confirmed": True})


def record_sent(settings, p: dict | None, name: str, to: str, first: bool) -> None:
    if first:
        tracker.drafted(settings, name, p, "email", (p or {}).get("country") or world.HOME, mockup=True)
    row, _ = tracker.track(settings, name, p, "contacted", "email")
    row["email"] = to
    rows = st.rows_of(settings, st.OUTREACH)
    for r in rows:
        if r.get("name", "").lower() == name.lower():
            r["email"] = to
    st.save(settings, st.OUTREACH, rows)
    tracker.sync_prospect(settings, row)


FREE_MAIL = {"gmail.com", "googlemail.com", "hotmail.com", "hotmail.co.uk", "outlook.com", "live.com", "live.co.uk",
             "yahoo.com", "yahoo.co.uk", "icloud.com", "me.com", "aol.com", "btinternet.com", "sky.com", "proton.me"}


def already_emailed(settings, to: str) -> str:
    """The business we already emailed at this address (or, for a company domain, anyone at it): branches of one
    business share an inbox, and nobody should get the same pitch twice."""
    to = to.lower().strip()
    domain = to.split("@")[-1]
    for r in st.rows_of(settings, st.OUTREACH):
        e = str(r.get("email") or "").lower().strip()
        if e and (e == to or (domain not in FREE_MAIL and e.split("@")[-1] == domain)):
            return r.get("name", "")
    return ""


def sent_today(ctx) -> int:
    return ctx.brain.count_today("warden", "win")


def watch_replies(ctx) -> list[str]:
    """Replies from anyone we emailed: opt-outs are honoured for good, other replies stop the follow-ups."""
    s = ctx.settings
    rows = st.rows_of(s, st.OUTREACH)
    emailed = {r["email"].lower(): r for r in rows if r.get("email") and r.get("status") == "contacted"}
    if not emailed:
        return []
    notes = []
    for msg in alfred_mail._messages(s, 14, 60, True):
        sender = email.utils.parseaddr(str(msg["From"] or ""))[1].lower()
        row = emailed.get(sender)
        if not row:
            continue
        text = alfred_mail.body_text(msg)[:1500]
        status = "opted out" if OPT_OUT_WORDS.search(text.split("On ")[0][:400]) else "replied"
        tracker.track(s, row["name"], None, status)
        tracker.sync_prospect(s, next(r for r in st.rows_of(s, st.OUTREACH) if r["name"] == row["name"]))
        emailed.pop(sender, None)
        notes.append(f"{row['name']} {'opted out (never contacted again)' if status == 'opted out' else 'REPLIED, answer them'}")
    return notes
