"""The LSX HQ agents (Kinetic Web Designs division). Each has one job, a schedule, and writes what it did to the shared brain.

They reuse Alfred's own Kinetic tools (lead finder, outreach drafts, follow-ups, briefing, content calendar,
Instagram replies), so nothing new talks to the outside world. Hard rules, same as Alfred's:
- nothing is ever SENT to a lead: Closer only drafts; the owner sends (Instagram replies to people who messaged
  first are Alfred's own job, and Concierge only watches them)
- keys and tokens are never logged
- writing is done by the free AI route (OmniRoute's alfred-free combo); nothing here spends Claude credit
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus

import httpx

from config import Settings
from hq.brain import Brain

UK_CITIES = ["Birmingham", "Manchester", "Leeds", "London", "Liverpool", "Bristol", "Sheffield", "Nottingham",
             "Leicester", "Croydon", "Glasgow", "Cardiff", "Newcastle", "Coventry", "Bradford", "Brighton"]
# The owner (23 Oct 2026): "we aren't limited to the UK". Half of Hawk's searches go abroad, to English-speaking
# places; kinetic_world still decides per country whether Vera may email or it goes on the DM list.
WORLD_CITIES = ["Dublin, Ireland", "New York, USA", "Sydney, Australia", "Lagos, Nigeria", "Houston, USA",
                "Cork, Ireland", "Melbourne, Australia", "Atlanta, USA", "Johannesburg, South Africa", "Chicago, USA",
                "Auckland, New Zealand", "Galway, Ireland", "Los Angeles, USA", "Accra, Ghana", "Brisbane, Australia",
                "Dallas, USA", "Nairobi, Kenya", "Miami, USA", "Dubai, UAE", "Cape Town, South Africa"]


@dataclass
class Agent:
    key: str
    name: str
    title: str
    emoji: str
    colour: str
    job: str
    every: int = 0                      # minutes between runs (0: use times)
    times: tuple = ()                   # ("09:05", "13:05"): once after each of these each day
    hours: tuple = (0, 24)              # only between these hours
    division: str = "Kinetic Web Designs"  # which LSX business this agent works for
    running: bool = field(default=False, compare=False)
    run: object = None                  # async fn(ctx) -> str

    def due(self, brain: Brain, now: datetime) -> bool:
        if self.running or not (self.hours[0] <= now.hour < self.hours[1]):
            return False
        last = brain.last_run(self.key)
        started = datetime.fromtimestamp(last["started"]) if last else None
        if self.every:
            return not started or now - started >= timedelta(minutes=self.every)
        today = now.date()
        slots = [datetime.combine(today, datetime.strptime(t, "%H:%M").time()) for t in self.times]
        passed = [s for s in slots if s <= now]
        return bool(passed) and (not started or started < passed[-1])

    def next_text(self, brain: Brain, now: datetime) -> str:
        if self.every:
            last = brain.last_run(self.key)
            if not last:
                return "now"
            nxt = datetime.fromtimestamp(last["started"]) + timedelta(minutes=self.every)
            return "now" if nxt <= now else f"{nxt:%H:%M}"
        future = [t for t in self.times if datetime.combine(now.date(), datetime.strptime(t, "%H:%M").time()) > now]
        return future[0] if future else f"tomorrow {self.times[0]}"


class Ctx:
    def __init__(self, settings: Settings, brain: Brain, http: httpx.AsyncClient):
        self.settings, self.brain, self.http = settings, brain, http

    async def ask_ai(self, prompt: str, max_tokens: int = 500) -> str:
        """One answer from the free AI route (OmniRoute). Raises on failure."""
        s = self.settings
        if not s.omniroute_url:
            raise RuntimeError("OmniRoute isn't set up")
        base = s.omniroute_url.rstrip("/")
        base = base if base.endswith("/v1") else base + "/v1"
        for tokens in (max_tokens, max_tokens * 3):  # thinking models can spend the budget before answering: retry once
            r = await self.http.post(f"{base}/chat/completions", timeout=120,
                                     headers={"Authorization": f"Bearer {s.omniroute_key or 'omniroute'}"},
                                     json={"model": s.omniroute_model or "auto", "max_tokens": tokens,
                                           "messages": [{"role": "user", "content": prompt}]})
            r.raise_for_status()
            text = ((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            if text.strip():
                return text.strip()
        raise RuntimeError("the free AI gave an empty answer")


# ---------------------------------------------------------------- the agents' work

async def guardian(ctx: Ctx) -> str:
    """Checks every part of the machine is up and says when something changes."""
    s, b, http = ctx.settings, ctx.brain, ctx.http

    async def up(url: str) -> bool:
        try:
            r = await http.get(url, timeout=15, follow_redirects=False)
            return r.status_code < 500
        except httpx.HTTPError:
            return False

    checks = {
        "alfred": await up(f"http://127.0.0.1:{s.port}/"),
        "omniroute": await up((s.omniroute_url or "http://localhost:20128").replace("/v1", "") + "/login") if s.omniroute_url else False,
        "website": await up("https://kineticwebdesigns.co.uk/"),
        "google_places": bool(s.google_places_key),
        "instagram": bool(s.instagram_token),
        "alfred_email": bool(s.alfred_email_app_password),
    }
    last_ai = b.get("health.ai_checked", 0)
    if time.time() - last_ai > 1800:  # the free AI itself, every 30 minutes
        try:
            await ctx.ask_ai("Reply with the single word OK.", 5)
            checks["free_ai"] = True
        except Exception:
            checks["free_ai"] = False
        b.set("health.ai_checked", time.time())
    else:
        checks["free_ai"] = b.get("health.free_ai", True)
    for k, ok in checks.items():
        before = b.get(f"health.{k}")
        b.set(f"health.{k}", ok)
        if before is not None and before != ok:
            b.log("guardian", f"{k.replace('_', ' ')} is {'back up' if ok else 'DOWN'}", "win" if ok else "error")
    down = [k for k, ok in checks.items() if not ok]
    return "all systems go" if not down else "needs attention: " + ", ".join(down)


async def concierge(ctx: Ctx) -> str:
    """Watches Alfred's Instagram inbox and comment replies and reports what happened."""
    import kinetic_store as st
    s, b = ctx.settings, ctx.brain
    state = st.load(s, "instagram-dms.json", {})
    if not state:
        return "no Instagram activity yet"
    counts = state.get("counts", {})
    needs = state.get("needs_you", [])
    before = b.get("ig.counts", {})
    for k, label, kind in (("replied", "answered {n} Instagram message(s)", "win"),
                           ("handed_off", "passed {n} Instagram message(s) to you", "warn")):
        n = counts.get(k, 0) - before.get(k, 0)
        if before and n > 0:
            b.log("concierge", label.format(n=n), kind)
    b.set("ig.counts", counts)
    b.set("ig.needs_you", [{"who": n.get("username"), "text": str(n.get("text", ""))[:120], "why": n.get("reason")}
                           for n in needs][-10:])
    return f"{counts.get('replied', 0)} answered, {len(needs)} waiting for you"


async def analyst(ctx: Ctx) -> str:
    """The money and the numbers: site sign-ups, briefs, payments and this week's five numbers."""
    import kinetic_briefing as kb
    s, b = ctx.settings, ctx.brain
    data = await asyncio.to_thread(kb.gather, s)
    text = kb.short_text(s, data)
    b.set("numbers.briefing", text)
    try:
        b.set("numbers.week", data.get("numbers"))
    except AttributeError:
        pass
    prev = b.get("numbers.last_text")
    if prev != text:
        b.log("analyst", text, "info")
        b.set("numbers.last_text", text)
    return "numbers updated"


def _trade(b: Brain) -> str:
    return b.get("settings.trade", "barbers")


async def scout(ctx: Ctx) -> str:
    """Finds fresh independent businesses with weak or no websites, round the UK and the world."""
    import kinetic_find as kf
    import kinetic_store as st
    s, b = ctx.settings, ctx.brain
    turn = b.get("scout.turn", 0)
    city = WORLD_CITIES[(turn // 2) % len(WORLD_CITIES)] if turn % 2 else UK_CITIES[(turn // 2) % len(UK_CITIES)]
    b.set("scout.turn", turn + 1)
    before = len(st.rows_of(s, st.PROSPECTS))
    trade = _trade(b)
    await kf.find(s, {"town": city, "kind": trade, "audit_limit": 8}, ctx.http)
    rows = st.rows_of(s, st.PROSPECTS)
    new = len(rows) - before
    no_site = sum(1 for r in rows[-max(new, 0):] if not r.get("website")) if new > 0 else 0
    b.log("scout", f"found {new} new {trade} leads in {city} ({no_site} with no website)", "win" if new else "info",
          {"city": city, "new": new})
    b.set("leads.total", len(rows))
    return f"{new} new leads in {city}"


async def closer(ctx: Ctx) -> str:
    """Writes today's first messages (with mock-ups) and the follow-ups that are due. Drafts only, never sends."""
    import kinetic_outreach as tracker
    import kinetic_sales as sales
    s, b = ctx.settings, ctx.brain
    per_run = int(b.get("settings.drafts_per_run", 10))
    daily = int(b.get("settings.drafts_per_day", 20))
    done_today = b.count_today("closer", "win")
    made, notes = 0, []
    for row in tracker.due_rows(s):
        if row.get("channel") == "email" and row.get("email"):
            continue  # Vera checks and sends email follow-ups herself
        try:
            out = await tracker.follow_up(s, {"business": row["name"]})
            b.log("closer", f"follow-up drafted for {row['name']}", "win", {"lead": row["name"], "type": "follow-up"})
            notes.append(str(out)[:300])
        except Exception as e:
            b.log("closer", f"couldn't draft the follow-up for {row['name']}: {e}", "warn")
    made = 0
    if not b.get(f"closer.dms.{datetime.now().date()}"):  # one list a day, at Blade's first run
        made = await dm_list(ctx, min(per_run, max(0, daily - done_today)))
    b.set("closer.last", datetime.now().isoformat(timespec="minutes"))
    return f"{made} Instagram DMs ready for you and {len(notes)} follow-ups drafted"


DM_FOLDER = Path.home() / "OneDrive" / "Desktop" / "Instagram DMs"


async def dm_list(ctx: Ctx, n: int) -> int:
    """The owner's morning list (asked for 23 Oct 2026): the best UK sole-trader leads, which the law doesn't let us
    cold-email, each with a free mock-up online and a ready-to-send DM. The owner sends them by hand on Instagram."""
    import kinetic_outreach as tracker
    import kinetic_world as world
    from hq import outbox
    s, b = ctx.settings, ctx.brain
    items = []
    looked = 0
    for p in outbox.sole_traders(s, outbox.limited_companies(b)):
        if len(items) >= n or looked >= n * 6:
            break
        if b.get(f"ig.none.{p['id']}"):
            continue
        looked += 1
        handle = p.get("instagram", "").lstrip("@") or await outbox.instagram_handle(ctx.http, p)
        if not handle:  # the owner needs an @name to find them (asked 23 Oct 2026): only shops that give one
            b.set(f"ig.none.{p['id']}", True)
            continue
        if b.get(f"ig.dm.{handle.lower()}"):
            await asyncio.to_thread(tracker.drafted, s, p["name"], p, "dm", p.get("country") or world.HOME, mockup=False)
            continue  # another branch already got a DM on this account: one message per inbox
        try:
            link = await outbox.make_mockup(ctx, p)  # Iris builds and checks it
            if not link:
                continue
            items.append((p, handle, link, outbox.dm_text(s, p, link)))
            if handle:
                b.set(f"ig.dm.{handle.lower()}", p["name"])
        except Exception as e:
            b.log("closer", f"couldn't make the mock-up for {p['name']}: {e}", "warn")
    if not items:
        return 0
    await asyncio.to_thread(outbox.deploy_site)
    today = datetime.now().date()
    file = DM_FOLDER / f"Instagram DMs {today.isoformat()}.md"
    old = file.read_text(encoding="utf-8") if file.exists() else ""
    start = old.count("\n## ") + 1
    lines = [] if old else [f"# Instagram DMs for {today.strftime('%A %d %B')}", "",
                            "Busy barbers and salons we can't email (UK sole traders, and countries where a sales "
                            "email needs consent). Search the @name on Instagram, paste the message, send, then tell "
                            "Alfred \"sent to <name>\" so the follow-ups are tracked.", ""]
    for i, (p, handle, link, text) in enumerate(items, start):
        where = f"@{handle}" if handle else "not on their website: search \"" + p["name"] + "\" on Instagram"
        lines += [f"## {i}. {p['name']} ({p.get('town', '')})", f"Instagram: {where}",
                  f"{p.get('rating')}★ from {p.get('reviews')} Google reviews · "
                  + (f"website: {p['website']}" if p.get("website") else "no website"),
                  f"Mock-up: {link}",
                  f"Video to attach (open on your phone, save, then add it to the DM): {link}preview.mp4"
                  if b.get("settings.mockup_video", False) and
                  (outbox.LIVE / "m" / outbox.slug(p["name"]) / "preview.mp4").exists() else "",
                  "", "```", text, "```", ""]
        await asyncio.to_thread(tracker.drafted, s, p["name"], p, "dm", p.get("country") or world.HOME, mockup=True)
        b.log("closer", f"DM ready for {p['name']} ({where}): mock-up {link}", "win", {"lead": p["name"], "type": "dm"})
    DM_FOLDER.mkdir(parents=True, exist_ok=True)
    text_all = (old.rstrip("\n") + "\n\n" if old else "") + "\n".join(lines)
    file.write_text(text_all, encoding="utf-8")
    b.set(f"closer.dms.{today}", str(file))
    b.set("closer.dms.latest", text_all)
    return len(items)


async def designer(ctx: Ctx) -> str:
    """Iris: upgrades mock-ups already sent out to the full version (their photos, hours, reviews, what it fixes),
    three a run, re-checking each, so every link we've given anyone shows our best work."""
    import kinetic_store as st
    from hq import outbox
    s, b = ctx.settings, ctx.brain
    ps = {p["name"]: p for p in st.rows_of(s, st.PROSPECTS)}
    done, held = 0, 0
    for r in st.rows_of(s, st.OUTREACH):
        p = ps.get(r["name"])
        if done + held >= 3 or not p or b.get(f"iris.{p['id']}"):
            continue
        if not (outbox.LIVE / "m" / outbox.slug(p["name"])).exists():
            continue
        link = await outbox.make_mockup(ctx, p)
        b.set(f"iris.{p['id']}", bool(link))
        done, held = done + bool(link), held + (not link)
    if done:
        await asyncio.to_thread(outbox.deploy_site)
    return f"{done} mock-ups upgraded and checked" + (f", {held} held back" if held else "") if done or held else \
        "every mock-up is up to date"


async def studio(ctx: Ctx) -> str:
    """Today's posts: what goes out and when, with the caption."""
    import kinetic_calendar as cal
    s, b = ctx.settings, ctx.brain
    line = await asyncio.to_thread(cal.reminder_line, s)
    text = line or "Today: post 2 videos at 6pm UK with the caption ending 'Comment SITE for a free home page mock-up'."
    b.log("studio", text, "info")
    b.set("studio.today", text)
    return "posting plan ready"


async def ceo(ctx: Ctx) -> str:
    """Reads the whole brain each morning and sets the day's three priorities."""
    b = ctx.brain
    snapshot = {
        "numbers": b.get("numbers.briefing"),
        "health": b.facts("health."),
        "instagram": b.get("ig.counts"),
        "waiting_for_owner": len(b.get("ig.needs_you", []) or []),
        "leads_total": b.get("leads.total"),
        "yesterday": [e["text"] for e in b.events(limit=40) if e["kind"] in ("win", "warn", "error")][-20:],
        "trade_of_the_week": _trade(b),
    }
    prompt = ("You are the CEO agent of Kinetic Web Designs, a small UK web design agency selling websites "
              "(Starter £395, Business £895, Online shop £1,595, Shopify redesign £595, setup £995) worldwide. "
              "Vera (quality control) checks and sends up to 15 cold emails a day; the owner sends 10 to 20 "
              "Instagram/WhatsApp DMs a day by hand and posts 2 videos a day at 6pm. "
              "From this snapshot of the business brain, write exactly 3 short, concrete priorities for today "
              "(one line each, numbered, plain English, most money-making first), then one line on the biggest risk. "
              "No preamble.\n\nSnapshot:\n" + json.dumps(snapshot, default=str)[:6000])
    try:
        plan = await ctx.ask_ai(prompt, 2000)
    except Exception as e:
        plan = ("1. Send today's outreach drafts (10–20). 2. Post the 2 videos at 6pm. "
                "3. Answer anything on the Instagram 'needs you' list.") + f" (AI unavailable: {type(e).__name__})"
    b.set("ceo.priorities", plan)
    b.log("ceo", "Today's priorities:\n" + plan, "win")
    return "priorities set"


async def warden(ctx: Ctx) -> str:
    """Vera, quality control: checks every outreach email and, as the owner asked (22 Oct 2026), sends the ones that
    pass without waiting for them, one per run, within the limits in hq/outbox.py."""
    from hq import outbox
    s, b = ctx.settings, ctx.brain
    if not b.get("settings.autosend", True):
        return "auto-send is off"
    for note in await asyncio.to_thread(outbox.watch_replies, ctx):
        b.log("warden", note, "warn" if "REPLIED" in note else "info")
    if not outbox.in_hours(outbox.uk_now()):
        return "outside sending hours (Mon to Sat, 9:00 to 17:30)"
    cap = int(b.get("settings.send_per_day", 15))
    if outbox.sent_today(ctx) >= cap:
        return f"today's limit reached ({cap} emails)"
    for row in _due_by_email(s):  # 1. an email follow-up that's due
        link = b.get(f"mockup.{row['name'].lower()}", "")
        made = outbox.follow_up_email(s, row["name"], link)
        if made:
            return await _vet_and_send(ctx, None, row["name"], row["email"], *made, link, first=False)
    looked = 0
    await outbox.check_companies(ctx)  # UK leads that are limited companies can be emailed too (PECR)
    for p in outbox.candidates(s, outbox.limited_companies(b)):  # 2. a first email to the best fresh lead we can email
        if b.get(f"skip.{p['id']}"):
            continue
        looked += 1
        to = await outbox.email_for(ctx, p)
        if not to:
            b.set(f"skip.{p['id']}", "no email address found")
            if looked >= 15:  # most small businesses list no email, so look further each run
                break
            continue
        twin = outbox.already_emailed(s, to)
        if twin:
            b.set(f"skip.{p['id']}", f"same inbox as {twin}, already emailed")
            continue
        link = await outbox.make_mockup(ctx, p)  # Iris builds and checks it
        if not link:
            b.set(f"skip.{p['id']}", "the mock-up didn't pass Iris's checks")
            continue
        await asyncio.to_thread(outbox.deploy_site)
        b.set(f"mockup.{p['name'].lower()}", link)
        subject, body = outbox.first_email(s, p, link)
        return await _vet_and_send(ctx, p, p["name"], to, subject, body, link, first=True)
    return "no fresh leads with an email address right now (Hawk will find more)"


def _due_by_email(s) -> list[dict]:
    import kinetic_outreach as tracker
    rows, seen = [], set()
    for r in tracker.due_rows(s):  # one follow-up per inbox, even when two branches share it
        if r.get("channel") == "email" and r.get("email") and r["email"].lower() not in seen:
            seen.add(r["email"].lower())
            rows.append(r)
    return rows


async def _vet_and_send(ctx: Ctx, p: dict | None, name: str, to: str, subject: str, body: str, link: str,
                        first: bool) -> str:
    from hq import outbox
    b = ctx.brain
    # US and Canadian law (CAN-SPAM, CASL) need a postal address; Alfred's template only asks for it there
    postal = b.get("settings.postal_address", "")
    if postal:
        body = body.replace("[your postal address]", postal)
    problems = outbox.rule_check(subject, body, link, first)
    if problems:
        if p:
            b.set(f"skip.{p['id']}", "failed checks: " + ", ".join(problems))
        b.log("warden", f"held back the email to {name}: " + ", ".join(problems), "warn")
        return f"held back {name}"
    ok, why = await outbox.ai_check(ctx, p or {"name": name}, subject, body)
    if not ok:
        if p:
            b.set(f"skip.{p['id']}", "editor said no: " + why)
        b.log("warden", f"held back the email to {name}. Editor's note: {why}", "warn")
        return f"held back {name}"
    await asyncio.to_thread(outbox.send, ctx.settings, to, subject, body)
    await asyncio.to_thread(outbox.record_sent, ctx.settings, p, name, to, first)
    kind = "first email" if first else "follow-up"
    b.log("warden", f"checked and sent the {kind} to {name} ({to.split('@')[1]}): \"{subject}\"", "win",
          {"lead": name, "type": kind, "link": link})
    return f"sent the {kind} to {name}"


def roster() -> list[Agent]:
    return [
        Agent("ceo", "Atlas", "CEO", "👑", "#f5c84c", "Reads the brain each morning and sets the day's 3 priorities.",
              times=("07:55",), run=ceo),
        Agent("scout", "Hawk", "Lead Hunter", "🦅", "#4cc9f0", "Finds fresh businesses with weak or no websites, UK and worldwide.",
              times=("08:30", "11:30", "14:30", "17:30"), run=scout),
        Agent("closer", "Blade", "Closer", "🗡️", "#f72585", "Each morning: your Instagram DM list (with @names and mock-ups), plus follow-ups due. Drafts only.",
              times=("09:05", "13:05"), run=closer),
        Agent("concierge", "Echo", "Concierge", "💬", "#b5179e", "Watches Instagram DMs and comments Alfred answers; flags what needs you.",
              every=2, run=concierge),
        Agent("analyst", "Ledger", "Analyst", "📊", "#4ade80", "Sign-ups, briefs, payments and the five weekly numbers.",
              every=60, hours=(7, 23), run=analyst),
        Agent("studio", "Reel", "Studio", "🎬", "#fb923c", "Today's posts, times and captions.",
              times=("08:40", "17:40"), run=studio),
        Agent("guardian", "Sentinel", "Guardian", "🛡️", "#94a3b8", "Keeps Alfred, the free AI, the website and every connection up.",
              every=5, run=guardian),
        Agent("warden", "Vera", "Quality Control", "🔍", "#a78bfa",
              "Double-checks every email (house rules plus a strict AI editor) and sends the ones that pass, within safe daily limits.",
              every=15, hours=(9, 18), run=warden),
        Agent("designer", "Iris", "Designer", "🎨", "#f4a261",
              "Builds every mock-up from the shop's own Google photos, hours and reviews, shows what their current site "
              "costs them, then checks it on a phone and a laptop before anyone sees it.",
              every=30, hours=(8, 20), run=designer),
    ]
