"""Kinetic Web Designs outreach tracker: who has been contacted, who replied, who is due a follow-up, and which
clients to ask for a Google review and a referral.

Each lead's outreach is kept in kinetic-outreach.json: its status (new, drafted, contacted, replied, interested, won,
live, not interested, opted out), the channel and date of each message the user says they sent, and a short history.
kinetic_sales records "drafted" by itself when it writes a first message, refuses to draft for anyone who opted out or
said no, and warns instead of drafting when a lead has already been messaged, so nobody gets the same pitch twice.

follow_ups lists leads who haven't replied and are due a follow-up: FOLLOW_UP_SCHEDULE days (3, 7, 14 and 21) after
the first message. That's four follow-ups (five messages) at most, then Alfred leaves them be; a reply or a "no" stops
them at once (owner, 28 Oct 2026). follow_up drafts the next one in the lead's language with the English underneath and
the same opt-out line as the first message: polite nudges with the payment terms, then a short last-chance note.

review_request: for a client marked won or live, a Google review request (with the user's review link from
JARVIS_KINETIC_REVIEW_LINK) and a referral note (recommend a business: when they go live you get a free month of
hosting and care). Founding clients, who had £100 off in return for an honest review and permission to show their
site, get a review reminder phrased around that agreement. ask_reviews lists won clients not asked yet (5 by default).

Once a day (after REMIND_HOUR, while a page is open) Alfred says how many leads are due a follow-up. He never sends
anything: every message is a draft signed "Alfred, Kinetic Web Designs" that the user sends themselves, and a status
only changes when the user says so.
"""

import asyncio
from datetime import date, datetime, timedelta

import kinetic_store as st
import kinetic_world as world
import screen
from config import Settings

NAMES = {"web_design_outreach"}
ACTIONS = ["mark", "leads", "follow_ups", "follow_up", "summary", "review_request", "ask_reviews"]
STATUSES = ["new", "drafted", "contacted", "replied", "interested", "won", "live", "not interested", "opted out"]
CLOSED = ("not interested", "opted out")  # never message them again
CLIENTS = ("won", "live")  # paying clients: their site is being built, or is live
TALKING = ("replied", "interested", *CLIENTS)  # they answered: reply to them, don't pitch or chase
FINDER_STATUS = {"contacted": "contacted", "won": "client", "live": "client", "not interested": "not interested",
                 "opted out": "not interested"}  # what the client finder's own status becomes
SUMMARY_GROUPS = {"New": ("new",), "Drafted": ("drafted",), "Contacted": ("contacted",),
                  "Replied": ("replied", "interested"), "Won": CLIENTS, "No": CLOSED}  # cards show 8 columns at most
FOLLOW_UP_SCHEDULE = (3, 7, 14, 21)  # days after the first message; owner, 28 Oct 2026: stop only at the 4th
FOLLOW_UP_DAYS = FOLLOW_UP_SCHEDULE[0]  # the first follow-up
LAST_FOLLOW_UP_DAYS = FOLLOW_UP_SCHEDULE[-1]  # the fourth and last
FOLLOW_UPS = len(FOLLOW_UP_SCHEDULE)
MAX_MESSAGES = FOLLOW_UPS + 1  # the first message and four follow-ups, then stop
REVIEW_BATCH = 5
REMINDED = "kinetic-outreach-reminded.json"
REMIND_HOUR = 9
CHECK_SECONDS = 600
MAX_HISTORY = 30


def day(value) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def channels() -> list[str]:
    import kinetic_sales  # here, not at the top: kinetic_sales imports this module
    return kinetic_sales.CHANNELS


def resolve(settings: Settings, rows: list[dict], who) -> tuple[str, dict | None, dict | None]:
    """The lead's name, its saved prospect (if any) and its tracker row (if any)."""
    name = st.need(who, "business", 80)
    p = st.find_prospect(st.rows_of(settings, st.PROSPECTS), name)
    if p:
        row = next((r for r in rows if r.get("prospect") == p["id"]), None) or \
            next((r for r in rows if r["name"].lower() == p["name"].lower()), None)
        return p["name"], p, row
    key = name.lower()
    row = next((r for r in rows if r["name"].lower() == key), None) or \
        next((r for r in rows if key in r["name"].lower()), None)
    return (row["name"] if row else name), None, row


def new_row(rows: list[dict], name: str, prospect: dict | None, country: str = "") -> dict:
    if len(rows) >= st.MAX_ROWS:
        raise ValueError("The outreach tracker is full. Remove some old prospects first.")
    row = {"id": st.next_id(rows), "name": name, "prospect": (prospect or {}).get("id"),
           "country": (prospect or {}).get("country") or country or "", "status": "new", "messages": 0, "history": []}
    rows.append(row)
    return row


def log(row: dict, status: str, on: date, channel: str = "") -> None:
    row["status"] = status
    row["updated"] = on.isoformat()
    row["history"] = (row.get("history") or [])[-(MAX_HISTORY - 1):] + [
        {"date": on.isoformat(), "status": status, **({"channel": channel} if channel else {})}]


def where_(row: dict) -> str:
    return world.country_name(row.get("country") or world.HOME)


def first_sent(row: dict) -> date | None:
    return day(row.get("contacted")) or day(row.get("last_contacted"))


def next_due(row: dict) -> date | None:
    """When the next follow-up is due (3, 7, 14 and 21 days after the first message), or None when there isn't one."""
    first, n = first_sent(row), row.get("messages", 0)
    if not first or not 1 <= n < MAX_MESSAGES:
        return None
    return first + timedelta(days=FOLLOW_UP_SCHEDULE[n - 1])


def days_text() -> str:
    return ", ".join(map(str, FOLLOW_UP_SCHEDULE[:-1])) + f" and {FOLLOW_UP_SCHEDULE[-1]}"


def is_last(row: dict) -> bool:
    """The next follow-up is the last one."""
    return row.get("messages", 0) == MAX_MESSAGES - 1


def sent_on(row: dict) -> str:
    last = day(row.get("last_contacted"))
    how = f" by {row['channel']}" if row.get("channel") else ""
    return f"{how} on {st.short(last)}" if last else how


# ---- recording -----------------------------------------------------------------------

def before_draft(settings: Settings, name: str, prospect: dict | None) -> str:
    """Why a first message shouldn't be drafted for this lead, or "" when it's fine. Raises for anyone who said no."""
    _, _, row = resolve(settings, st.rows_of(settings, st.OUTREACH), (prospect or {}).get("name") or name)
    status = (row or {}).get("status", "new")
    if status in CLOSED:
        raise ValueError(f"{row['name']} is marked {status}, so I won't draft anything for them. "
                         "They've asked not to hear from you, and that's final.")
    if status == "contacted":
        due = next_due(row)
        when = (f" If they haven't replied by {st.short(due)}, I can draft "
                f"{'their last, short follow-up' if is_last(row) else 'a polite follow-up'}.") if due else \
            f" They've had {row.get('messages', 0)} messages already, so it's best to leave them be."
        return (f"Heads up: you already messaged {row['name']}{sent_on(row)}, so I haven't drafted another first "
                f"message. No double messaging.{when}")
    if status in TALKING:
        return (f"{row['name']} is already marked {status}, so a first pitch would be odd now. Reply to them directly "
                "instead; I can help with a quote or a mock-up.")
    return ""


def drafted(settings: Settings, name: str, prospect: dict | None, channel: str, country: str,
            contact_name: str = "", mockup: bool | None = None) -> None:
    """Called by kinetic_sales after a first-message draft: the lead becomes "drafted" (never moves a lead back).
    mockup notes whether the free mock-up went with it, for the briefing's "mock-ups sent" number."""
    rows = st.rows_of(settings, st.OUTREACH)
    _, prospect, row = resolve(settings, rows, (prospect or {}).get("name") or name)
    row = row or new_row(rows, name, prospect, country)
    if row["status"] in ("new", "drafted"):
        log(row, "drafted", st.today(), channel)
    row["drafted"] = st.today().isoformat()
    row["draft_channel"] = channel
    row["country"] = row.get("country") or country
    if contact_name:
        row["contact_name"] = contact_name
    if mockup is not None:
        row["mockup"] = bool(mockup)
    st.save(settings, st.OUTREACH, rows)


def track(settings: Settings, name: str, prospect: dict | None, status: str, channel: str = "",
          on: date | None = None, founding: bool | None = None) -> tuple[dict, str]:
    """Record a status the user told Alfred about. Returns the row and anything worth adding to the reply."""
    if status not in STATUSES:
        raise ValueError("Mark it as one of " + ", ".join(STATUSES) + ".")
    on = on or st.today()
    if on > st.today():
        raise ValueError("That date is in the future. Tell me once it has happened.")
    rows = st.rows_of(settings, st.OUTREACH)
    _, prospect, row = resolve(settings, rows, (prospect or {}).get("name") or name)
    row = row or new_row(rows, (prospect or {}).get("name") or name, prospect)
    note = ""
    if status == "contacted":
        if row["status"] in CLOSED:
            raise ValueError(f"{row['name']} is marked {row['status']}, so they shouldn't be messaged again. "
                             "I haven't recorded it.")
        channel = channel or row.get("channel") or row.get("draft_channel") or ""
        same = row.get("last_contacted") == on.isoformat() and (row.get("channel") or "") == channel
        if not same:  # telling Alfred twice about the same message doesn't count it twice
            row["messages"] = row.get("messages", 0) + 1
        row["contacted"] = min(row.get("contacted") or on.isoformat(), on.isoformat())  # the first message
        row["last_contacted"] = max(on.isoformat(), row.get("last_contacted") or "")
        row["channel"] = channel
        if row["status"] in TALKING:  # still talking: keep where they are, just note the message
            row["history"] = (row.get("history") or [])[-(MAX_HISTORY - 1):] + [
                {"date": on.isoformat(), "status": "contacted", **({"channel": channel} if channel else {})}]
        else:
            log(row, "contacted", on, channel)
            first = first_sent(row)
            if row["messages"] == 1:
                note = (f" If they haven't replied by {st.short(first + timedelta(days=FOLLOW_UP_DAYS))}, I'll remind "
                        f"you about a polite follow-up; {FOLLOW_UPS} in all, the last on "
                        f"{st.short(first + timedelta(days=LAST_FOLLOW_UP_DAYS))}.")
            elif row["messages"] < MAX_MESSAGES:
                n = row["messages"] - 1
                note = (f" That's follow-up {n} of {FOLLOW_UPS}. If they still haven't replied by "
                        f"{st.short(next_due(row))}, I'll remind you about "
                        f"{'one last short note' if is_last(row) else 'the next one'}.")
            elif row["messages"] == MAX_MESSAGES:
                note = (f" That's their last follow-up: {MAX_MESSAGES} messages in all. If they don't reply, I'll "
                        "leave them be.")
            elif not same:
                note = f" That's {row['messages']} messages now; best to leave them be unless they reply."
    else:
        log(row, status, on, channel)
        if status in TALKING or status in CLOSED:
            row[status.replace(" ", "_")] = on.isoformat()
        if status in CLOSED:
            note = " I won't draft anything for them again."
        elif status in CLIENTS and not row.get("review_asked"):
            note = (" Their site is live, so it's a good time to ask for a Google review and a referral: say "
                    f"\"ask {row['name']} for a review\"." if status == "live" else
                    " Once their site is live, I can draft a Google review request and a referral note for them.")
    if founding is not None:
        row["founding"] = bool(founding)
    st.save(settings, st.OUTREACH, rows)
    return row, note


def sync_prospect(settings: Settings, row: dict) -> None:
    """Keep the client finder's own status in step, without moving a lead or a client backwards."""
    rows = st.rows_of(settings, st.PROSPECTS)
    p = next((r for r in rows if row.get("prospect") and r.get("id") == row["prospect"]), None)
    target = FINDER_STATUS.get(row["status"])
    if not p or not target:
        return
    if target == "contacted":
        p["contacted"] = p.get("contacted") or row.get("contacted") or st.today().isoformat()
        if p.get("status", "new") == "new":
            p["status"] = "contacted"
    else:
        p["status"] = target
    st.save(settings, st.PROSPECTS, rows)


def from_finder(settings: Settings, prospect: dict, status: str) -> None:
    """The client finder's "mark" keeps the tracker in step (contacted, client, not interested)."""
    mapped = {"contacted": "contacted", "client": "won", "not interested": "not interested"}.get(status)
    if mapped:
        try:
            track(settings, prospect["name"], prospect, mapped)
        except ValueError:  # e.g. they opted out: the tracker keeps its answer
            pass


def mark(settings: Settings, args: dict) -> str:
    status = str(args.get("status") or "").strip().lower().replace("_", " ")
    channel = str(args.get("channel") or "").strip().lower()
    if channel and channel not in channels():
        raise ValueError("Which kind of message? " + ", ".join(channels()) + ".")
    on = st.parse_date(args.get("date"), "date")
    founding = args.get("founding") if isinstance(args.get("founding"), bool) else None
    row, note = track(settings, args.get("business") or args.get("client"), None, status, channel, on, founding)
    sync_prospect(settings, row)
    when = "" if (on or st.today()) == st.today() else f" on {st.short(on)}"
    if status == "contacted":
        return f"Noted: you messaged {row['name']}{f' by {channel}' if channel else ''}{when}.{note}"
    return f"{row['name']} is now marked {row['status']}{when}.{note}"


# ---- lists ---------------------------------------------------------------------------

def all_leads(settings: Settings) -> list[dict]:
    """Tracked leads plus saved prospects not tracked yet (as "new")."""
    rows = st.rows_of(settings, st.OUTREACH)
    tracked = {r.get("prospect") for r in rows if r.get("prospect")}
    names = {r["name"].lower() for r in rows}
    for p in st.rows_of(settings, st.PROSPECTS):
        if p.get("id") not in tracked and p["name"].lower() not in names:
            rows.append({"name": p["name"], "prospect": p.get("id"), "country": p.get("country", ""), "status": "new",
                         "messages": 0})
    return rows


def due_rows(settings: Settings, on: date | None = None) -> list[dict]:
    """Leads with no reply whose next follow-up is due (3 days, then 7, after the first message): oldest first."""
    on = on or st.today()
    out = [r for r in st.rows_of(settings, st.OUTREACH) if r.get("status") == "contacted" and
           (d := next_due(r)) and d <= on]
    return sorted(out, key=lambda r: (next_due(r), r["name"].lower()))


def lead_rows(rows: list[dict]) -> list[list[str]]:
    return [[r["name"], r["status"], where_(r), r.get("channel") or r.get("draft_channel") or "-",
             st.short(day(r["last_contacted"])) if day(r.get("last_contacted")) else "-",
             str(r.get("messages", 0))] for r in rows]


COLUMNS = ["Lead", "Status", "Country", "Channel", "Last message", "Messages"]


def leads(settings: Settings, args: dict) -> screen.Shown:
    rows = all_leads(settings)
    status = str(args.get("status") or "").strip().lower().replace("_", " ")
    if status:
        rows = [r for r in rows if r["status"] == status]
    if args.get("country"):
        code = world.country_code(args["country"])
        rows = [r for r in rows if (r.get("country") or world.HOME) == code]
    if not rows:
        raise ValueError("No leads like that yet. Find some prospects or draft an outreach message first.")
    rows.sort(key=lambda r: (STATUSES.index(r["status"]) if r["status"] in STATUSES else 0, r["name"].lower()))
    return st.table(f"{len(rows)} lead{'s' if len(rows) != 1 else ''}.", "Outreach tracker", COLUMNS,
                    lead_rows(rows[:60]))


def due_name(r: dict) -> str:
    return r["name"] + (" (last one)" if is_last(r) else "")


def follow_ups(settings: Settings, args: dict) -> screen.Shown | str:
    due = due_rows(settings)
    if not due:
        return (f"Nobody is due a follow-up. A lead who hasn't replied gets follow-ups on days "
                f"{days_text()} after your first message, the last a short one, then I leave them be.")
    rows = [[r["name"], f"{r.get('messages', 1)} of {FOLLOW_UPS}" + (" (last)" if is_last(r) else ""), where_(r), r.get("channel") or "-",
             st.short(first_sent(r)), f"{(st.today() - first_sent(r)).days} days"] for r in due]
    n = len(due)
    return st.table(f"{n} lead{'s are' if n != 1 else ' is'} due a follow-up: " + ", ".join(due_name(r) for r in due[:5])
                    + (" and more" if n > 5 else "") + f". {FOLLOW_UPS} follow-ups at most: days {days_text()}. "
                    "I'll draft them, you send them.", "Due a follow-up",
                    ["Lead", "Follow-up", "Country", "Channel", "First message", "Since"], rows,
                    [{"label": "Draft follow-up", "say": f"Draft a follow-up for {due[0]['name']}."}])


def summary(settings: Settings, args: dict) -> screen.Shown:
    rows = all_leads(settings)
    if not rows:
        raise ValueError("No leads yet. Find some prospects or draft an outreach message first.")
    by_status = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    countries: dict[str, dict[str, int]] = {}
    for r in rows:
        countries.setdefault(where_(r), {s: 0 for s in STATUSES})[r["status"]] += 1
    due = len(due_rows(settings))
    text = (f"{len(rows)} lead{'s' if len(rows) != 1 else ''}: " +
            ", ".join(f"{n} {s}" for s, n in by_status.items() if n) + ". By country: " +
            ", ".join(f"{c} {sum(v.values())}" for c, v in sorted(countries.items(), key=lambda x: -sum(x[1].values())))
            + "." + (f" {due} {'are' if due != 1 else 'is'} due a follow-up." if due else ""))
    def cells(label: str, counts: dict[str, int]) -> list[str]:
        return [label] + [str(sum(counts[s] for s in group)) for group in SUMMARY_GROUPS.values()] + \
            [str(sum(counts.values()))]
    table_rows = [cells(c, v) for c, v in sorted(countries.items())] + [cells("All", by_status)]
    return st.table(text, "Outreach summary", ["Country", *SUMMARY_GROUPS, "Total"], table_rows)


# ---- the follow-up draft ---------------------------------------------------------------

def follow_up_draft(settings: Settings, args: dict) -> dict:
    """The English follow-up and what goes with it, or a "stop" reason when one shouldn't be sent."""
    import kinetic_sales  # here, not at the top: kinetic_sales imports this module
    rows = st.rows_of(settings, st.OUTREACH)
    name, prospect, row = resolve(settings, rows, args.get("business") or args.get("client"))
    status = (row or {}).get("status", "new")
    if status in CLOSED:
        raise ValueError(f"{name} is marked {status}, so I won't draft anything for them.")
    if status in TALKING:
        return {"stop": f"{name} has already replied, so there's nothing to chase. Answer them directly."}
    if status != "contacted":
        return {"stop": f"You haven't told me you've messaged {name} yet. Say \"I emailed {name}\" once you've sent "
                        "the first message."}
    if row.get("messages", 0) >= MAX_MESSAGES:
        return {"stop": f"{name} has had {row['messages']} messages with no reply, so I'll leave them be. "
                        f"{FOLLOW_UPS} follow-ups is the limit."}
    sent = first_sent(row) or st.today()
    last = is_last(row)
    due = next_due(row) or st.today()
    if st.today() < due:
        waited = (st.today() - sent).days
        return {"stop": f"You first messaged {name} {waited} day{'s' if waited != 1 else ''} ago. Give them until "
                        f"{st.short(due)} before {'their last' if last else 'a'} follow-up."}
    p = prospect or {}
    me = st.business(settings)
    country = world.country_code(args.get("country")) or row.get("country") or p.get("country") or world.HOME
    channel = args.get("channel") or row.get("channel") or row.get("draft_channel") or world.default_channel(country)
    if channel not in kinetic_sales.CHANNELS:
        raise ValueError("Which kind of message? " + ", ".join(kinetic_sales.CHANNELS) + ".")
    contact = st.clean(args.get("contact_name") or row.get("contact_name"), 40)
    hello = f"Hi {contact}," if contact else "Hi there,"
    sign = st.sign_off(me)
    first = {"email": "email", "letter": "letter", "dm": "message", "whatsapp": "WhatsApp message", "phone": "call",
             "visit": "visit"}.get(
        row.get("channel") or "", "message")
    store = kinetic_sales.store_lead(p)  # a Shopify store: the store makeover and the redesign price
    gift = "store makeover" if store else "example home page"
    offer = (f"The free {gift} I made for you is still yours to see, with no obligation."
             if args.get("mockup", True) else "I'd still be happy to share a few free ideas, with no obligation.")
    pr = kinetic_sales.prices(settings)
    start = world.local_price(pr["packages"]["shopify_redesign" if store else "starter"]["price"],
                              world.currency_of(country))
    terms = world.payment_terms(pr["deposit_percent"])
    price = ((f"A Shopify store redesign is {start}, and you pay {terms}. You keep paying Shopify directly for your "
              "plan." if store else f"Websites start from {start}, and you pay {terms}.")
             if args.get("price", True) else "")
    if last:  # the second and last follow-up: a short last-chance note, no price
        nudge = f"One last note from me about {name}'s website, and then I'll leave you in peace."
        offer = (f"The free {'store makeover' if store else 'home page mock-up'} I made for you is still yours if "
                 "you'd like it: just reply \"yes\" and I'll send it again." if args.get("mockup", True) else
                 "If you'd ever like a few free ideas for it, just reply \"yes\".")
        price = ""
        bow_out = "If I don't hear back, I'll take it that now isn't the right time, and I won't message again."
    elif row.get("messages", 0) >= 2:  # the 2nd and 3rd follow-ups: a different opening each time
        nudge = (f"I'm checking in once more about {name}'s website, in case my earlier {first}s got buried."
                 if row.get("messages", 0) == 2 else
                 f"A quick note about {name}'s website, as I know my earlier {first}s may have landed at a busy time.")
        bow_out = "If now isn't the right time, that's absolutely fine."
    else:
        nudge = f"I'm just following up on my {first} from {st.short(sent)} about {name}'s website. I know how busy " \
                "running a business is, so I'll keep this short."
        bow_out = "If now isn't the right time, that's absolutely fine."
    offer = f"{offer} {st.PREVIEW}"  # every follow-up says it too
    opt_out = world.OPT_OUT
    subject = f"Last note: {name}'s website" if last else f"Following up: {name}'s website"
    if channel == "email":
        address = me["address"] or ("[your postal address]" if world.rules_of(country) in ("us", "ca") else "")
        body = (f"Subject: {subject}\n\n{hello}\n\n{nudge}\n\n{offer}\n\n"
                + (f"{price}\n\n" if price else "") + f"{bow_out}\n\nThanks,\n{sign}"
                + "".join(f"\n{x}" for x in (me["phone"], me["website"], address) if x) + f"\n\n{opt_out}")
    elif channel == "letter":
        body = (f"{me['name']}\n{me['address'] or '[your address]'}\n{st.long_date(st.today())}\n\nTo the owner, {name}\n\n"
                f"{hello.replace('Hi', 'Dear')}\n\n{nudge}\n\n{offer}\n\n" + (f"{price}\n\n" if price else "") +
                f"{bow_out}\n\nYou can reach us on {me['phone'] or '[your phone]'} or {me['email'] or '[your email]'}.\n\n"
                f"Kind regards,\n{sign}\n\n{opt_out}")
    elif channel in ("phone", "visit"):
        body = (f"{'Phone' if channel == 'phone' else 'Walk-in'} {'last ' if last else ''}follow-up script for {name}\n\n"
                f"1. \"Hi, it's {me['name']}. We {'called' if first == 'call' else 'got in touch'} on "
                f"{st.short(sent)} about your website. Have you got a minute?\"\n2. \"{offer}\"\n"
                + (f"3. If they ask about price: \"{price}\"\n" if price else "") +
                f"{'4' if price else '3'}. \"{bow_out}\"\n"
                + ("This is the last time: if they say no or don't answer, thank them and leave it there." if last else
                   "If they say no, thank them and don't get in touch again."))
    else:
        body = (f"{hello} {nudge} {offer} " + (f"{price} " if price else "") + f"{bow_out} {sign}"
                f"\n\n{opt_out}")
    return {"name": name, "channel": channel, "country": country, "last": last,
            "language": world.language_code(args.get("language"), country), "body": body}


async def follow_up(settings: Settings, args: dict) -> screen.Shown | str:
    import kinetic_sales  # here, not at the top: kinetic_sales imports this module
    d = await asyncio.to_thread(follow_up_draft, settings, args)
    if "stop" in d:
        return d["stop"]
    name, channel, body, language = d["name"], d["channel"], d["body"], d["language"]
    said = ""
    if language != "en" and channel in kinetic_sales.TRANSLATED:
        local = await world.translate(settings, body, language)
        if local:
            body = f"{local}\n\n----------\nEnglish version:\n\n{body}"
            said = f" in {world.LANGUAGES[language]} with the English underneath"
        else:
            said = f" in English only, as I couldn't translate it into {world.LANGUAGES[language]} just now"
    path = await asyncio.to_thread(st.write, settings, ("Clients", name),
                                   f"Outreach follow-up {channel} {st.today().isoformat()}.md", body + "\n")

    def keep() -> None:
        rows = st.rows_of(settings, st.OUTREACH)
        row = resolve(settings, rows, name)[2]
        if row:
            row["follow_up_drafted"] = st.today().isoformat()
            st.save(settings, st.OUTREACH, rows)
    await asyncio.to_thread(keep)
    which = ("It's their last follow-up; once you've sent it, tell me and I'll leave them be unless they reply."
             if d["last"] else f"It's one of {FOLLOW_UPS} follow-ups; once you've sent it, tell me, and if they still "
                               f"don't reply I'll remind you about the next (the last on day {LAST_FOLLOW_UP_DAYS}).")
    kind = "a short last follow-up" if d["last"] else "a polite follow-up"
    return st.text_card(f"I drafted {kind} {channel} for {name}{said} and saved it in "
                        f"{st.where(settings, path)}. {st.NOT_SENT} {which}", f"Follow-up: {name}", body, [
                            {"label": "Mark sent", "say": f"I sent the follow-up {channel} to {name}."},
                            {"label": "They replied", "say": f"{name} replied."}])


# ---- reviews and referrals ---------------------------------------------------------------

REVIEW_LINK_GAP = "[your Google review link]"


def founding_client(settings: Settings, row: dict | None, name: str) -> bool:
    """Marked as a founding client, or quoted with the founding client offer."""
    if row and isinstance(row.get("founding"), bool):
        return row["founding"]
    return any(q.get("founding_discount") and q["client"].lower() == name.lower()
               for q in st.rows_of(settings, st.QUOTES))


def clients(settings: Settings) -> list[dict]:
    """Won or live clients: from the tracker, accepted quotes and the client finder ("client")."""
    rows = [r for r in st.rows_of(settings, st.OUTREACH) if r.get("status") in CLIENTS]
    names = {r["name"].lower() for r in rows}
    extra = [q["client"] for q in st.rows_of(settings, st.QUOTES) if q.get("status") == "accepted"]
    extra += [p["name"] for p in st.rows_of(settings, st.PROSPECTS) if p.get("status") == "client"]
    for name in extra:
        tracked = next((r for r in st.rows_of(settings, st.OUTREACH) if r["name"].lower() == name.lower()), None)
        if name.lower() not in names and not (tracked and tracked.get("status") in CLOSED):
            names.add(name.lower())
            rows.append(tracked or {"name": name, "status": "won", "messages": 0})
    return rows


def review_drafts(settings: Settings, name: str, contact: str, founding: bool) -> tuple[str, str]:
    """(Google review request, referral note), both signed by Alfred for the business."""
    me = st.business(settings)
    link = settings.kinetic_review_link or REVIEW_LINK_GAP
    hello = f"Hi {contact}," if contact else "Hi there,"
    sign = f"Thanks,\n{st.sign_off(me)}"
    if founding:
        review = (f"Subject: Your founding client review for {me['name']}\n\n{hello}\n\n"
                  f"Thank you again for being one of our founding clients. As part of the founding client offer, "
                  f"{name} had £100 off its website in return for an honest Google review and permission to show "
                  f"the site as an example of our work.\n\nNow that your site is ready, would you leave that review? "
                  f"It only takes a minute:\n\n{link}\n\nAn honest sentence or two about working with us is "
                  f"perfect, good or bad. Thank you for helping us get started.\n\n{sign}")
    else:
        review = (f"Subject: Could you leave {me['name']} a quick Google review?\n\n{hello}\n\n"
                  f"Thank you again for choosing {me['name']} for {name}'s new website. If you're happy with it, a "
                  f"quick Google review would mean a lot to a small business like ours. It only takes a minute:\n\n"
                  f"{link}\n\nA sentence or two about how you found working with us is perfect.\n\n{sign}")
    contact_us = " or ".join(x for x in (me["website"], me["email"]) if x)
    referral = (f"Subject: Know a business that needs a website?\n\n{hello}\n\n"
                f"If you know a business owner who needs a new website, we'd love to help them too. Recommend a "
                f"business to us, and when their website goes live you get a free month of hosting and care, as a "
                f"thank-you.\n\nJust reply with their name and the best way to reach them"
                + (f", or pass on our details: {contact_us}" if contact_us else "") + f".\n\n{sign}")
    return review, referral


def review_request(settings: Settings, args: dict) -> screen.Shown | str:
    rows = st.rows_of(settings, st.OUTREACH)
    name, prospect, row = resolve(settings, rows, args.get("business") or args.get("client"))
    client = next((c for c in clients(settings) if c["name"].lower() == name.lower()), None)
    if not client:
        status = (row or {}).get("status", "new")
        if status in CLOSED:
            raise ValueError(f"{name} is marked {status}, so I won't draft anything for them.")
        return (f"{name} isn't a client yet (they're {status}), so it's too early to ask for a review. Mark them won "
                "or live once they've paid and their site is up.")
    founding = args["founding"] if isinstance(args.get("founding"), bool) else founding_client(settings, row, name)
    contact = st.clean(args.get("contact_name") or (row or {}).get("contact_name"), 40)
    review, referral = review_drafts(settings, name, contact, founding)
    review_path = st.write(settings, ("Clients", name), f"Review request {st.today().isoformat()}.md", review + "\n")
    st.write(settings, ("Clients", name), f"Referral note {st.today().isoformat()}.md", referral + "\n")
    if not row:
        row = new_row(rows, name, prospect)
    if row["status"] not in CLIENTS:  # e.g. an accepted quote: they're a client now
        log(row, "won", st.today())
    row["review_asked"] = row["referral_asked"] = st.today().isoformat()
    if founding:
        row["founding"] = True
    if contact:
        row["contact_name"] = contact
    st.save(settings, st.OUTREACH, rows)
    gap = "" if settings.kinetic_review_link else (
        " Your Google review link isn't set yet, so the draft says [your Google review link]: put it in "
        "JARVIS_KINETIC_REVIEW_LINK in .env, or paste it in before sending.")
    kind = "a founding client review reminder" if founding else "a Google review request"
    return st.text_card(f"I drafted {kind} and a referral note for {name} and saved them in "
                        f"{st.where(settings, review_path.parent)}. {st.NOT_SENT}{gap}", f"Review and referral: {name}",
                        f"{review}\n\n----------\n\n{referral}", [
                            {"label": "Next client", "say": "Which clients haven't I asked for a review?"}])


def ask_reviews(settings: Settings, args: dict) -> screen.Shown | str:
    """Won clients not asked for a review yet: founding clients first, then the longest-standing."""
    count = max(1, min(int(args.get("count") or REVIEW_BATCH), 20))
    waiting = [c for c in clients(settings) if not c.get("review_asked")]
    if not waiting:
        return ("Every won client has been asked for a review. Mark a client won or live when you get a new one."
                if clients(settings) else "No won clients yet. Mark a lead won or live once they've paid.")
    waiting.sort(key=lambda c: (not founding_client(settings, c, c["name"]), c.get("updated") or "", c["name"].lower()))
    pick = waiting[:count]
    rows = [[c["name"], c.get("status") or "won", "yes" if founding_client(settings, c, c["name"]) else "-",
             st.short(day(c["updated"])) if day(c.get("updated")) else "-"] for c in pick]
    text = (f"{len(waiting)} client{'s' if len(waiting) != 1 else ''} not asked for a Google review yet. "
            f"Here {'are' if len(pick) != 1 else 'is'} {len(pick)}: " + ", ".join(c["name"] for c in pick) +
            ". Say \"ask <client> for a review\" and I'll draft the review request and a referral note.")
    return st.table(text, "Ask for reviews", ["Client", "Status", "Founding", "Since"], rows,
                    [{"label": f"Ask {c['name']}", "say": f"Draft a review request for {c['name']}."} for c in pick[:3]])


# ---- the daily reminder -----------------------------------------------------------------

def reminder_line(settings: Settings, now: datetime | None = None) -> str:
    """Once a day, from REMIND_HOUR: what to say about follow-ups that are due ("" when there's nothing to say)."""
    now = now or datetime.now()
    if now.hour < REMIND_HOUR or st.load(settings, REMINDED, {}).get("date") == now.date().isoformat():
        return ""
    st.save(settings, REMINDED, {"date": now.date().isoformat()})
    due = due_rows(settings, now.date())
    if not due:
        return ""
    n = len(due)
    return (f"{settings.user_address.capitalize()}, {n} Kinetic lead{'s are' if n != 1 else ' is'} due a follow-up: "
            + ", ".join(due_name(r) for r in due[:3]) + (" and more" if n > 3 else "") +
            ". Say \"draft the follow-ups\" when you're ready.")


async def watch(settings: Settings, announce, someone_there) -> None:
    """Say once a day how many leads are due a follow-up, waiting until a page is open."""
    while True:
        try:
            if someone_there() and (text := await asyncio.to_thread(reminder_line, settings)):
                await announce(text, "sales")
        except Exception as exc:  # a bad file must not stop the watcher
            print(f"[jarvis] Outreach reminder: {exc!r}", flush=True)
        await asyncio.sleep(CHECK_SECONDS)


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_design_outreach",
        "description": "Kinetic Web Designs outreach tracker: who has been contacted, who is due a follow-up, and "
                       "review and referral requests for clients. "
                       "mark: record a lead's status when the user says so: contacted (\"I emailed Joe's Barbers\", "
                       "with channel and date if given), replied, interested, won, live (their site is up), not "
                       "interested, or opted out (\"they said no thanks\"); founding true for a founding client. "
                       "Drafting a first message with web_design_sales outreach records "
                       "drafted by itself. leads: the list (filter by status or country). follow_ups: leads due a "
                       f"follow-up: days {days_text()} after the first message. follow_up: the next follow-up "
                       "draft in their language (polite nudges, then a short last-chance note); "
                       f"{FOLLOW_UPS} follow-ups at most, then stop; a reply or a no stops them. summary: "
                       "counts per status and per country. review_request: for a won or live client, a Google review "
                       "request (founding clients: phrased around their £100-off-for-a-review agreement) and a "
                       "referral note (a free month of hosting and care when a business they recommend goes live). "
                       "ask_reviews: won clients not asked for a review yet (count, default 5). Never draft for "
                       "anyone opted out or not interested. Drafts only, signed \"Alfred, Kinetic Web Designs\": "
                       "never send anything, and only mark a lead contacted when the user says they sent it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "business": {"type": "string", "description": "The lead: a saved prospect's number or name, or any "
                                                              "business name."},
                "status": {"type": "string", "enum": STATUSES, "description": "mark: the new status. leads: filter."},
                "channel": {"type": "string", "enum": channels(), "description": "mark: how they were contacted. "
                                                                                 "follow_up: default the first one."},
                "date": {"type": "string", "description": "mark: when it happened, YYYY-MM-DD or 'yesterday' "
                                                          "(default today)."},
                "country": {"type": "string", "description": "leads: filter by country."},
                "contact_name": {"type": "string", "description": "follow_up, review_request: the owner's first name "
                                                                  "if known."},
                "language": {"type": "string", "description": "follow_up: write it in this language; default the "
                                                              "lead's country's."},
                "price": {"type": "boolean", "description": "follow_up: mention the starting price (default true)."},
                "mockup": {"type": "boolean", "description": "follow_up: mention the free mock-up (default true)."},
                "founding": {"type": "boolean", "description": "mark, review_request: a founding client (had £100 "
                                                              "off for an honest Google review and permission to "
                                                              "show their site)."},
                "count": {"type": "integer", "description": "ask_reviews: how many clients (default 5)."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    if args.get("action") == "follow_up":  # async: it may ask Claude for a translation
        return await follow_up(settings, args)
    handlers = {"mark": mark, "leads": leads, "follow_ups": follow_ups, "follow_up": follow_up, "summary": summary,
                "review_request": review_request, "ask_reviews": ask_reviews}
    return await asyncio.to_thread(st.dispatch, handlers, args.get("action"), settings, args, "outreach tracker")
