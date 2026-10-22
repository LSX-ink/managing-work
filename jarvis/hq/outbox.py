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


def candidates(settings) -> list[dict]:
    """Fresh, busy, money-making leads with a website where a cold email is allowed: most likely to reply first.
    Quiet businesses (few reviews, low rating) are left out entirely."""
    rows = st.rows_of(settings, st.OUTREACH)
    by_name = {r["name"].lower(): r for r in rows}
    out = []
    for p in st.rows_of(settings, st.PROSPECTS):
        if not p.get("website") or kf.social_only(p):
            continue
        if closed_or_busy(by_name.get(p["name"].lower())):
            continue
        country = p.get("country") or world.HOME
        if not world.cold_email_ok(country, p["name"]):
            continue
        if busy_score(p) <= 0:
            continue
        out.append(p)
    return sorted(out, key=busy_score, reverse=True)


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

def publish_mockup(settings, p: dict) -> str:
    """Make the lead's mock-up and put it online at kineticwebdesigns.co.uk/m/<name>/ (hidden from Google)."""
    sales.outreach_mockup(settings, {"client": p["id"]})
    html = (st.folder(settings, "Mockups", p["name"]) / "index.html").read_text(encoding="utf-8")
    if "noindex" not in html:
        html = html.replace("<head>", '<head><meta name="robots" content="noindex, nofollow">', 1)
    out = LIVE / "m" / slug(p["name"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    r = subprocess.run(["npx.cmd", "--yes", "wrangler", "pages", "deploy", ".", "--cwd", str(LIVE), "--project-name",
                        "kinetic", "--branch", "main", "--commit-dirty=true"], capture_output=True, text=True,
                       timeout=300)
    if r.returncode != 0:
        raise RuntimeError("couldn't put the mock-up online: " + (r.stderr or r.stdout)[-200:])
    return f"{SITE}/m/{slug(p['name'])}/"


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
