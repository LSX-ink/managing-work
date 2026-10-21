"""Kinetic Web Designs morning money briefing: what came in since yesterday and who to deal with today.

"Alfred, morning briefing" (and once a day by himself from BRIEF_HOUR, while a page is open) pulls together:
new sign-ups and briefs on kineticwebdesigns.co.uk since the start of yesterday, Stripe payments and refunds the site's
webhook saved in the D1 payments table, where the follow-up email series is at (all read-only through kinetic_site's
safe wrangler runner), leads due a follow-up (kinetic_outreach), unpaid and overdue invoices (kinetic_invoices) and the
best leads nobody has contacted yet (ranked the way the client finder ranks them).

It also gives the five numbers that run the business, for this week (from Monday) and last week: messages sent
(outreach the user marked sent), replies, mock-ups sent (first messages that carried one), briefs (the site's D1
briefs table) and deposits and payments (invoices marked paid, or the Stripe card payments in D1 if those count
more), with the conversion at each step against the target funnel (100 messages, 10 replies, 3 briefs, 1 client)
and a one-line "fix this step" hint for the weakest one. Only data Alfred already keeps or already reads is used.

Alfred speaks a short version; the full briefing is saved as Kinetic Web Designs/Briefings/Morning briefing <date>.md,
shown on the screen, and listed in the HUD notifications when it comes by itself. When wrangler, Node or the internet
isn't there, the website parts say so in a line and the rest of the briefing still comes. Nothing is sent or changed.
"""

import asyncio
from datetime import date, datetime, time, timedelta

import kinetic_find
import kinetic_invoices
import kinetic_outreach
import kinetic_site
import kinetic_store as st
from config import Settings

NAMES = {"kinetic_briefing"}
ACTIONS = ["briefing", "last"]
LAST_RUN = "kinetic-briefing-last.json"
BRIEF_HOUR = 9
CHECK_SECONDS = 600
FIRST_LOOK = 60  # seconds after start before the first check, so a quick restart (or a test) never runs wrangler
MAX_LIST = 10
CONTACT_TODAY = 3
SKIP_REST = ("logged in", "Node.js", "too long", "internet", "couldn't find")  # wrangler can't work at all just now
TARGET = {"messages": 100, "replies": 10, "briefs": 3, "payments": 1}  # a week's funnel: 100 -> 10 -> 3 -> 1
MIN_BASE = {("replies", "messages"): 20, ("briefs", "replies"): 3, ("deposits", "briefs"): 2}  # before judging a rate
STEPS = [  # (step, count, out of, target rate, what to do when it's the weakest)
    ("messages", "messages", "", TARGET["messages"],
     "send more first messages: about 20 each weekday, batched with the trade of the week and a walk-in route."),
    ("mock-ups", "mockups", "messages", 1.0,
     "send the free mock-up (and its 30-second video) with every first message; it's the hook."),
    ("replies", "replies", "messages", TARGET["replies"] / TARGET["messages"],
     "open with their single biggest problem, keep it short, and DM or WhatsApp the no-website leads instead of "
     "emailing them."),
    ("briefs", "briefs", "replies", TARGET["briefs"] / TARGET["replies"],
     "answer replies within the hour and send them to the brief form: \"see your design before you pay anything\"."),
    ("deposits", "payments", "briefs", TARGET["payments"] / TARGET["briefs"],
     "send the quote and mock-up within a day of each brief, then follow up: half when we start building, half "
     "once everything's complete."),
]


def start_of_yesterday(now: datetime) -> int:
    """Milliseconds since 1970 at local midnight at the start of yesterday, as the site stores times."""
    midnight = now.astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    return int((midnight - timedelta(days=1)).timestamp() * 1000)


def money(pence, currency: str) -> str:
    amount = int(pence or 0) / 100
    symbol = {"gbp": "£", "usd": "$", "eur": "€"}.get(str(currency or "").lower())
    return f"{symbol}{amount:,.2f}" if symbol else f"{amount:,.2f} {str(currency or '').upper()}".strip()


# ---- gathering ---------------------------------------------------------------------

def site_part(settings: Settings, since: int, weeks: tuple[int, int] | None = None) -> dict:
    """Sign-ups, briefs, payments and the email series from D1, plus this week's and last week's brief and payment
    counts when weeks (the two Mondays, in ms) is given. Each part is {"error": reason} when it can't be read."""
    out: dict = {}
    offline = ""

    def ask(key: str, read):
        nonlocal offline
        if offline:
            out[key] = {"error": offline}
            return
        try:
            out[key] = read()
        except ValueError as exc:
            out[key] = {"error": str(exc)}
            if any(word in str(exc) for word in SKIP_REST):
                offline = str(exc)  # no point waiting on wrangler again for the next part

    ask("signups", lambda: {k: int(v or 0) for k, v in (kinetic_site.wrangler(
        "SELECT COUNT(*) AS n, COALESCE(SUM(marketing), 0) AS opted_in FROM signups "
        f"WHERE created_at >= {int(since)}") or [{}])[0].items()})
    ask("briefs", lambda: {"rows": [kinetic_site._brief(r) for r in kinetic_site.wrangler(
        "SELECT id, created_at, name, business, email, phone, data FROM briefs "
        f"WHERE created_at >= {int(since)} ORDER BY created_at DESC LIMIT {MAX_LIST}")]})
    ask("payments", lambda: payments(since))
    ask("series", lambda: {"text": str(kinetic_site.series(settings, {}))})
    if weeks:
        this, last = (int(x) for x in weeks)
        ask("week_briefs", lambda: week_counts(kinetic_site.wrangler(
            "SELECT COUNT(*) AS n, SUM(CASE WHEN created_at >= " f"{this} THEN 1 ELSE 0 END) AS this_week "
            f"FROM briefs WHERE created_at >= {last}")))
        ask("week_payments", lambda: week_counts([r for r in kinetic_site.wrangler(
            f"SELECT kind, status, COUNT(*) AS n, SUM(CASE WHEN created >= {this} THEN 1 ELSE 0 END) AS this_week "
            f"FROM payments WHERE created >= {last} GROUP BY kind, status")
            if r.get("kind") == "payment" and r.get("status") == "succeeded"]))
    return out


def week_counts(rows: list[dict]) -> dict:
    """{"this": n, "last": n} from rows of COUNT(*) AS n (since last Monday) and this_week (since this Monday)."""
    total = sum(int(r.get("n") or 0) for r in rows)
    this = sum(int(r.get("this_week") or 0) for r in rows)
    return {"this": this, "last": max(0, total - this)}


def mondays(day: date) -> tuple[date, date]:
    """(this Monday, last Monday)."""
    this = day - timedelta(days=day.weekday())
    return this, this - timedelta(days=7)


def ms(day: date) -> int:
    return int(datetime.combine(day, time()).astimezone().timestamp() * 1000)


def tracker_week(settings: Settings, start: date, end: date) -> dict:
    """Messages sent, replies and mock-ups sent between start and end (inclusive), from the outreach tracker."""
    def within(value) -> bool:
        d = kinetic_outreach.day(value) if value else None
        return bool(d and start <= d <= end)
    messages = replies = mockups = 0
    for r in st.rows_of(settings, st.OUTREACH):
        history = r.get("history") or []
        sent = {(h.get("date"), h.get("channel", "")) for h in history if h.get("status") == "contacted"}
        if not sent:  # an older row with only its dates
            sent = {(d, "") for d in {r.get("contacted"), r.get("last_contacted")} if d}
        messages += sum(1 for d, _ in sent if within(d))
        answered = sorted([h.get("date") for h in history if h.get("status") in ("replied", "interested")] +
                          [r.get(k) for k in ("replied", "interested") if r.get(k)])
        replies += bool(answered) and within(answered[0])
        first = kinetic_outreach.first_sent(r)
        mockups += bool(first and start <= first <= end) and r.get("mockup") is not False
    return {"messages": messages, "replies": int(replies), "mockups": int(mockups)}


def numbers(settings: Settings, site: dict, today: date) -> dict:
    """This week's and last week's five numbers ({"this": {...}, "last": {...}}); briefs is None if unknown."""
    this_monday, last_monday = mondays(today)
    spans = {"this": (this_monday, today), "last": (last_monday, this_monday - timedelta(days=1))}
    paid = [r for r in st.rows_of(settings, st.INVOICES) if r.get("status") == "paid" and r.get("paid_on")]
    briefs, cards = site.get("week_briefs") or {}, site.get("week_payments") or {}
    out = {}
    for key, (start, end) in spans.items():
        row = tracker_week(settings, start, end)
        local = sum(1 for r in paid if start.isoformat() <= r["paid_on"] <= end.isoformat())
        row["briefs"] = None if "error" in briefs or key not in briefs else briefs[key]
        row["payments"] = max(local, 0 if "error" in cards else int(cards.get(key) or 0))
        out[key] = row
    return out


def pct(part, whole) -> str:
    return f"{round(100 * part / whole)}%" if part is not None and whole else "-"


def weakest(nums: dict) -> tuple[str, str]:
    """(step, hint) for the step furthest below the target funnel, over both weeks."""
    both = {k: (None if nums["this"][k] is None or nums["last"][k] is None else nums["this"][k] + nums["last"][k])
            for k in nums["this"]}
    best = None
    for step, count, of, rate, hint in STEPS:
        have, base = both[count], (2 if not of else both[of])
        if have is None or base is None or base < MIN_BASE.get((step, of), 1):
            continue  # too few to judge a rate yet
        score = (have / base) / rate
        if best is None or score < best[0]:
            best = (score, step, hint)
    if best is None or best[0] >= 1:
        return ("", "every step is on target; keep the messages going.") if best else \
            ("messages", STEPS[0][4])
    return best[1], best[2]


def numbers_lines(nums: dict) -> list[str]:
    """The five numbers as a Markdown table, with conversions and the fix-this-step line."""
    def cell(key, count, of=""):
        n = nums[key][count]
        if n is None:
            return "couldn't check"
        return f"{n} ({pct(n, nums[key][of])})" if of else str(n)
    rows = [("Messages sent", "messages", ""), ("Mock-ups sent", "mockups", "messages"),
            ("Replies", "replies", "messages"), ("Briefs", "briefs", "replies"),
            ("Deposits and payments", "payments", "briefs")]
    step, hint = weakest(nums)
    lines = ["| | This week | Last week |", "|---|---|---|"]
    lines += [f"| {label} | {cell('this', c, o)} | {cell('last', c, o)} |" for label, c, o in rows]
    lines += ["", f"Target each week: {TARGET['messages']} messages, {TARGET['replies']} replies, {TARGET['briefs']} "
              f"briefs, {TARGET['payments']} client. Percentages are of the step before.",
              f"Fix this step{f' ({step})' if step else ''}: {hint}"]
    return lines


def payments(since: int) -> dict:
    """Stripe payments and refunds saved by the site's webhook (the payments table, amounts in pence)."""
    try:
        rows = kinetic_site.wrangler("SELECT kind, status, amount, currency, customer, description, created "
                                     f"FROM payments WHERE created >= {int(since)} ORDER BY created DESC LIMIT 20")
    except ValueError as exc:
        if "tables I expected" in str(exc):
            return {"error": "the payments table isn't on the site's database yet (it comes with the Stripe webhook)"}
        raise
    paid = [r for r in rows if r.get("kind") == "payment" and r.get("status") == "succeeded"]
    refunds = [r for r in rows if r.get("kind") == "refund" and r.get("status") == "succeeded"]
    failed = [r for r in rows if r.get("status") == "failed"]
    totals: dict[str, int] = {}
    for r in paid:
        cur = str(r.get("currency") or "gbp").lower()
        totals[cur] = totals.get(cur, 0) + int(r.get("amount") or 0)
    return {"paid": paid, "refunds": refunds, "failed": failed, "totals": totals}


def contact_today(settings: Settings, limit: int = CONTACT_TODAY) -> list[dict]:
    """The best leads nobody has messaged yet, ranked the way the client finder ranks prospects."""
    prospects = {p.get("id"): p for p in st.rows_of(settings, st.PROSPECTS)}
    fresh = [r for r in kinetic_outreach.all_leads(settings) if r.get("status") == "new"]

    def key(r):
        p = prospects.get(r.get("prospect"))
        # not in the finder: ranked like an unchecked site
        return kinetic_find.rank_key(p) if p else (kinetic_find.UNCHECKED, 0, 0, r["name"])
    out = []
    for r in sorted(fresh, key=key)[:limit]:
        p = prospects.get(r.get("prospect")) or {}
        why = kinetic_find.headline(p)[1] if p else "not checked yet"
        out.append({"name": r["name"], "why": why, "phone": p.get("phone") or "", "email": p.get("email") or ""})
    return out


def gather(settings: Settings, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    today = now.date()
    invoices = [r for r in st.rows_of(settings, st.INVOICES) if r.get("status") == "unpaid"]
    late = [r for r in invoices if kinetic_invoices.state(r, today).startswith("overdue")]
    this_monday, last_monday = mondays(today)
    site = site_part(settings, start_of_yesterday(now), (ms(this_monday), ms(last_monday)))
    return {"date": today, "site": site, "follow_ups": kinetic_outreach.due_rows(settings, today),
            "unpaid": invoices, "overdue": late, "contact": contact_today(settings),
            "numbers": numbers(settings, site, today)}


# ---- writing it up -----------------------------------------------------------------

def _n(count: int, word: str) -> str:
    return f"{count} {word}{'s' if count != 1 else ''}"


def full_text(settings: Settings, b: dict) -> str:
    """The whole briefing as Markdown."""
    s, day = b["site"], b["date"]
    lines = [f"# Morning briefing: {st.long_date(day)}", "", "Kinetic Web Designs, since the start of yesterday.", ""]
    if b.get("numbers"):
        lines += ["## Your five numbers", ""] + numbers_lines(b["numbers"]) + [""]
    lines += ["## Website", ""]
    su = s.get("signups", {})
    lines.append(f"- Sign-ups: couldn't check ({su['error']})" if "error" in su else
                 f"- Sign-ups: {su.get('n', 0)} new, {su.get('opted_in', 0)} ticked the box for tips and offers")
    br = s.get("briefs", {})
    if "error" in br:
        lines.append(f"- Briefs: couldn't check ({br['error']})")
    else:
        lines.append(f"- Briefs: {len(br['rows'])} new")
        lines += [f"  - {x['name']} at {x['business']} ({x['when']}): {kinetic_site.asked_for(x)}" for x in br["rows"]]
    lines += ["", "## Payments", ""]
    pay = s.get("payments", {})
    if "error" in pay:
        lines.append(f"- Couldn't check payments: {pay['error']}")
    elif not (pay["paid"] or pay["refunds"] or pay["failed"]):
        lines.append("- No card payments since yesterday.")
    else:
        lines += [f"- Paid: {money(r.get('amount'), r.get('currency'))} from {r.get('customer') or 'a customer'}"
                  + (f" ({r['description']})" if r.get("description") else "") for r in pay["paid"]]
        lines += [f"- Refunded: {money(r.get('amount'), r.get('currency'))} to {r.get('customer') or 'a customer'}"
                  for r in pay["refunds"]]
        lines += [f"- Failed: {money(r.get('amount'), r.get('currency'))} from {r.get('customer') or 'a customer'}"
                  for r in pay["failed"]]
    lines += ["", "## Follow-ups due today", ""]
    lines += [f"- {r['name']}: messaged {st.short(kinetic_outreach.day(r['last_contacted']))}"
              + (f" by {r['channel']}" if r.get("channel") else "") for r in b["follow_ups"]] or ["- Nobody is due."]
    lines += ["", "## Invoices", ""]
    if not b["unpaid"]:
        lines.append("- Nothing unpaid.")
    lines += [f"- {r['number']} {r['client']}: {st.gbp(r['total'])}, {kinetic_invoices.state(r, b['date'])} "
              f"(due {r['due']})" for r in b["unpaid"]]
    lines += ["", "## Email series", ""]
    se = s.get("series", {})
    lines.append(f"- Couldn't check ({se['error']})" if "error" in se else f"- {se['text']}")
    lines += ["", "## Who to contact today", ""]
    lines += [f"- {c['name']}: {c['why']}" + (f", {c['phone']}" if c["phone"] else "")
              + (f", {c['email']}" if c["email"] else "") for c in b["contact"]] or \
        ["- No new leads waiting. Ask me to find some prospects."]
    lines += ["", "Everything is a draft or a reminder: nothing has been sent or changed."]
    return "\n".join(lines) + "\n"


def short_text(settings: Settings, b: dict) -> str:
    """A few spoken sentences."""
    s, bits = b["site"], []
    su, br, pay = s.get("signups", {}), s.get("briefs", {}), s.get("payments", {})
    if "error" in su and "error" in br:
        bits.append("I couldn't reach the website's database")
    else:
        if "error" not in su:
            bits.append(_n(su.get("n", 0), "new sign-up"))
        if "error" not in br:
            rows = br["rows"]
            bits.append(_n(len(rows), "new brief") + (f" ({', '.join(x['business'] for x in rows[:2])})" if rows else ""))
    if "error" not in pay and pay.get("totals"):
        bits.append(" and ".join(money(v, k) for k, v in pay["totals"].items()) + " paid by card")
    text = f"Since yesterday: {', '.join(bits)}." if bits else ""
    todo = []
    if b["follow_ups"]:
        todo.append(_n(len(b["follow_ups"]), "follow-up") + " due")
    if b["overdue"]:
        todo.append(f"{_n(len(b['overdue']), 'invoice')} overdue ({st.gbp(sum(r['total'] for r in b['overdue']))})")
    elif b["unpaid"]:
        todo.append(f"{_n(len(b['unpaid']), 'invoice')} unpaid")
    if todo:
        text += f" Today: {', '.join(todo)}."
    if b["contact"]:
        text += f" Contact today: {', '.join(c['name'] for c in b['contact'])}."
    text = text.strip() or "A quiet morning: nothing new and nothing due."
    if b.get("numbers"):
        w = b["numbers"]["this"]
        step = weakest(b["numbers"])[0]
        replies = f"{w['replies']} repl{'y' if w['replies'] == 1 else 'ies'}"
        text += (f" This week so far: {_n(w['messages'], 'message')} sent, {replies}"
                 + (f", {_n(w['briefs'], 'brief')}" if w["briefs"] is not None else "")
                 + f", {_n(w['payments'], 'payment')}." + (f" The step to fix is {step}." if step else ""))
    return text


def notification_text(settings: Settings, b: dict, where: str) -> str:
    """The HUD notification: the short version plus where the full one is."""
    return f"Morning briefing. {short_text(settings, b)} Full briefing: {where}."


def save(settings: Settings, b: dict):
    return st.write(settings, ("Briefings",), f"Morning briefing {b['date'].isoformat()}.md", full_text(settings, b),
                    replace=True)


def briefing(settings: Settings, args: dict):
    b = gather(settings)
    path = save(settings, b)
    st.save(settings, LAST_RUN, {"date": b["date"].isoformat()})
    return st.file_shown(settings, path, f"{settings.user_address.capitalize()}, your morning briefing. "
                         f"{short_text(settings, b)} The full version is on the screen and saved in "
                         f"{st.where(settings, path)}.", [
                             {"label": "Draft the follow-ups", "say": "Draft the follow-ups that are due."},
                             {"label": "Reply to new emails", "say": "Draft replies to my new emails."}])


def last(settings: Settings, args: dict):
    folder = st.folder(settings, "Briefings")
    found = sorted(folder.glob("Morning briefing *.md"))
    if not found:
        raise ValueError("There's no saved briefing yet. Say \"morning briefing\" for one now.")
    return st.file_shown(settings, found[-1], f"Your last briefing is on the screen ({st.where(settings, found[-1])}).")


# ---- once a day by himself -----------------------------------------------------------

def due(settings: Settings, now: datetime | None = None) -> bool:
    """True once a day, from BRIEF_HOUR, and records it so it isn't given twice (even after a restart)."""
    now = now or datetime.now()
    if now.hour < BRIEF_HOUR or st.load(settings, LAST_RUN, {}).get("date") == now.date().isoformat():
        return False
    st.save(settings, LAST_RUN, {"date": now.date().isoformat()})
    return True


def daily(settings: Settings, now: datetime | None = None) -> tuple[str, str]:
    """(spoken, notification) for the daily briefing, or ("", "") when it isn't due yet or was given today."""
    if not due(settings, now):
        return "", ""
    b = gather(settings, now)
    path = save(settings, b)
    where = st.where(settings, path)
    return (f"Good morning, {settings.user_address}. Your Kinetic briefing: {short_text(settings, b)} "
            "The full version is in your notifications."), notification_text(settings, b, where)


async def watch(settings: Settings, announce, someone_there) -> None:
    """Give the briefing once a day from BRIEF_HOUR, waiting until a page is open."""
    await asyncio.sleep(FIRST_LOOK)
    while True:
        try:
            if someone_there():
                spoken, shown = await asyncio.to_thread(daily, settings)
                if spoken:
                    await announce(spoken, "briefing", shown)
        except Exception as exc:  # a bad file or a missing tool must not stop the watcher
            print(f"[jarvis] Morning briefing: {exc!r}", flush=True)
        await asyncio.sleep(CHECK_SECONDS)


def tool_definitions() -> list[dict]:
    return [{
        "name": "kinetic_briefing",
        "description": "Kinetic Web Designs morning money briefing (\"morning briefing\", \"what came in?\"). "
                       "briefing: new website sign-ups and briefs since yesterday, Stripe payments, follow-ups due "
                       "today, unpaid and overdue invoices, where the email series is at and the best leads to "
                       "contact today; a short spoken summary, the full version on screen and saved as a .md in "
                       "Kinetic Web Designs/Briefings. last: show the last saved briefing. Read-only: nothing is sent.",
        "input_schema": {
            "type": "object",
            "properties": {"action": {"type": "string", "enum": ACTIONS}},
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"briefing": briefing, "last": last}
    return await asyncio.to_thread(st.dispatch, handlers, args.get("action") or "briefing", settings, args,
                                   "briefing")
