"""The outbox: first emails and email follow-ups that go out on their own, once Vera (quality control) passes them.

The owner asked for this (21 Oct 2026): emails shouldn't wait for their approval; an 8th agent double-checks every
email before it goes. DMs and WhatsApp still go by hand (Instagram doesn't allow apps to message first).

Guard rails, all enforced here, before anything is sent:
- only where a cold email is allowed: kinetic_world.cold_email_ok (UK PECR: limited companies only; never in the
  countries where cold email needs consent)
- never to anyone opted out, not interested, already talking to us, or already emailed today
- at most settings.send_per_day emails a day (default 15), one per run, only Monday to Saturday 09:00 to 17:30 UK
- every email: the business's real problem, the free mock-up as a link, "See your design before you pay anything",
  half when we start building and half once complete, signed Alfred, an opt-out line, no placeholders, no Klarna
- then the free AI reads it as a strict editor and must answer APPROVE
- replies are watched: an opt-out ("no thanks", "unsubscribe", "stop") marks them opted out for good; any other
  reply marks them replied (no more follow-ups) and puts them on the owner's list
Sent emails go from Alfred's own address and are recorded in the outreach tracker, so follow-ups come at day 3 and 7.
"""

import asyncio
import email.utils
import json
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
    return sorted(out, key=busy_score, reverse=True)


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
    ok, _ = await designer.build(ctx, p, LIVE / "m" / slug(p["name"]), st.business(ctx.settings)["name"])
    return f"{SITE}/m/{slug(p['name'])}/" if ok else ""


def deploy_site() -> None:
    r = subprocess.run(["npx.cmd", "--yes", "wrangler", "pages", "deploy", ".", "--cwd", str(LIVE), "--project-name",
                        "kinetic", "--branch", "main", "--commit-dirty=true"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=300)
    if r.returncode != 0:
        raise RuntimeError("couldn't put the mock-up online: " + (r.stderr or r.stdout)[-200:])


IG_LINK = re.compile(r"instagram\.com/([A-Za-z0-9_.]{2,30})", re.I)
IG_NOT_A_NAME = {"p", "reel", "reels", "explore", "accounts", "stories", "tv", "about", "developer", "legal",
                 "sharer", "share", "invites", "direct", "web", "embed"}


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
    (r"title|description|meta", "your site doesn't tell Google what you do, so you show up less in searches"),
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


def dm_text(settings, p: dict, link: str, brain=None) -> str:
    """The Instagram DM the owner sends by hand (asked 23 Oct 2026 for "a nice message" with the link): warm, about
    them first (their real Google rating), their one biggest website problem, then the mock-up made from their own
    photos and reviews, the no-risk terms, and an easy way to say no."""
    name = _base_name(p)
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
    if isinstance(speed, int) and speed < 50:
        problem = (problem + " " if problem else "") + f"Google also scores your site just {speed}/100 for speed on phones."
    gap = (f"One thing I spotted: {problem}" if problem else
           ("Your website doesn't show off how good you are yet." if p.get("website") else
            "You don't have a website yet, so people who find you on Google can't see your work or book easily."))
    return (f"Hi {name} team! \U0001F44B\n\nI came across you on Google, and {praise}\n\n{gap} So I put together a free "
            f"concept of what your website could look like, using your own photos and reviews:\n{link}\n\n"
            "It's yours to look at, no catch. If you love it, we can make it real, and you only pay half when we "
            "start and half once it's finished.\n\nWould love to hear what you think!\nAlfred, Kinetic Web Designs\n\n"
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


def first_email(settings, p: dict, link: str) -> tuple[str, str]:
    d = sales.outreach_draft(settings, {"client": p["id"]}, "email")
    subject, body = split_subject(d["body"])
    file = sales.store_mockup_file(p["name"]) if d.get("store") else sales.mockup_file(p["name"])
    body = re.sub(r"It's attached \(" + re.escape(file) + r"\), so you can open it on your phone\.",
                  f"You can open it on your phone here: {link}", body)
    # the opening already names their biggest problem: don't repeat it as the first suggestion
    opening = body.split("\n\n")[1].lower() if body.count("\n\n") > 1 else ""
    lines = body.split("\n")
    keep = [ln for ln in lines if not (ln.startswith("- ") and ln[2:].split(":")[0].lower() in opening)]
    if any(ln.startswith("- ") for ln in keep):
        body = "\n".join(keep)
    if body.count("\n- ") == 1:
        body = body.replace("A couple of things I'd suggest:", "One thing I'd also suggest:")
    return subject, body


def follow_up_email(settings, name: str, link: str) -> tuple[str, str] | None:
    d = tracker.follow_up_draft(settings, {"business": name, "channel": "email"})
    if d.get("stop"):
        return None
    subject, body = split_subject(d["body"])
    if link:
        body = body.replace("is still yours to see, with no obligation.", f"is still yours to see, with no obligation: {link}")
    return subject, body


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
              "Alfred; it has an opt-out line. Reply with ONLY JSON: {\"approve\": true|false, \"reason\": \"...\"}.\n\n"
              f"Business facts: {json.dumps({k: p.get(k) for k in ('name', 'kind', 'town', 'country', 'website', 'rating', 'reviews')})}\n\n"
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
