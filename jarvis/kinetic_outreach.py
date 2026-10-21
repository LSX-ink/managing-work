"""Kinetic Web Designs outreach tracker: who has been contacted, who replied, and who is due one follow-up.

Each lead's outreach is kept in kinetic-outreach.json: its status (new, drafted, contacted, replied, interested, won,
not interested, opted out), the channel and date of each message the user says they sent, and a short history.
kinetic_sales records "drafted" by itself when it writes a first message, refuses to draft for anyone who opted out or
said no, and warns instead of drafting when a lead has already been messaged, so nobody gets the same pitch twice.

follow_ups lists leads first messaged FOLLOW_UP_DAYS or more days ago who haven't replied. A lead gets at most one
follow-up (two messages in all); after that Alfred leaves them be. follow_up drafts that one polite message in the
lead's language with the English underneath, the same opt-out line as the first message and the same payment terms.

Once a day (after REMIND_HOUR, while a page is open) Alfred says how many leads are due a follow-up. He never sends
anything: every message is a draft the user sends themselves, and a status only changes when the user says so.
"""

import asyncio
from datetime import date, datetime, timedelta

import kinetic_store as st
import kinetic_world as world
import screen
from config import Settings

NAMES = {"web_design_outreach"}
ACTIONS = ["mark", "leads", "follow_ups", "follow_up", "summary"]
STATUSES = ["new", "drafted", "contacted", "replied", "interested", "won", "not interested", "opted out"]
CLOSED = ("not interested", "opted out")  # never message them again
TALKING = ("replied", "interested", "won")  # they answered: reply to them, don't pitch or chase
FINDER_STATUS = {"contacted": "contacted", "won": "client", "not interested": "not interested",
                 "opted out": "not interested"}  # what the client finder's own status becomes
SUMMARY_GROUPS = {"New": ("new",), "Drafted": ("drafted",), "Contacted": ("contacted",),
                  "Replied": ("replied", "interested"), "Won": ("won",), "No": CLOSED}  # cards show 8 columns at most
FOLLOW_UP_DAYS = 5
MAX_MESSAGES = 2  # the first message and one follow-up, then stop
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
        due = day(row.get("last_contacted"))
        when = f" If they haven't replied by {st.short(due + timedelta(days=FOLLOW_UP_DAYS))}, I can draft one " \
               "polite follow-up." if due and row.get("messages", 0) < MAX_MESSAGES else \
            " They've had two messages already, so it's best to leave them be."
        return (f"Heads up: you already messaged {row['name']}{sent_on(row)}, so I haven't drafted another first "
                f"message. No double messaging.{when}")
    if status in TALKING:
        return (f"{row['name']} is already marked {status}, so a first pitch would be odd now. Reply to them directly "
                "instead; I can help with a quote or a mock-up.")
    return ""


def drafted(settings: Settings, name: str, prospect: dict | None, channel: str, country: str,
            contact_name: str = "") -> None:
    """Called by kinetic_sales after a first-message draft: the lead becomes "drafted" (never moves a lead back)."""
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
    st.save(settings, st.OUTREACH, rows)


def track(settings: Settings, name: str, prospect: dict | None, status: str, channel: str = "",
          on: date | None = None) -> tuple[dict, str]:
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
        row["contacted"] = row.get("contacted") or on.isoformat()
        row["last_contacted"] = max(on.isoformat(), row.get("last_contacted") or "")
        row["channel"] = channel
        if row["status"] in TALKING:  # still talking: keep where they are, just note the message
            row["history"] = (row.get("history") or [])[-(MAX_HISTORY - 1):] + [
                {"date": on.isoformat(), "status": "contacted", **({"channel": channel} if channel else {})}]
        else:
            log(row, "contacted", on, channel)
            if row["messages"] == 1:
                note = f" If they haven't replied by {st.short(on + timedelta(days=FOLLOW_UP_DAYS))}, I'll remind you " \
                       "about one polite follow-up."
            elif row["messages"] == MAX_MESSAGES:
                note = " That's their follow-up done: two messages in all. If they don't reply, I'll leave them be."
            elif not same:
                note = f" That's {row['messages']} messages now; best to leave them be unless they reply."
    else:
        log(row, status, on, channel)
        if status in TALKING or status in CLOSED:
            row[status.replace(" ", "_")] = on.isoformat()
        if status in CLOSED:
            note = " I won't draft anything for them again."
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
    row, note = track(settings, args.get("business") or args.get("client"), None, status, channel, on)
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
    """Leads messaged once, FOLLOW_UP_DAYS or more days ago, with no reply: oldest first."""
    on = on or st.today()
    out = [r for r in st.rows_of(settings, st.OUTREACH) if r.get("status") == "contacted" and
           r.get("messages", 0) < MAX_MESSAGES and (d := day(r.get("last_contacted"))) and
           (on - d).days >= FOLLOW_UP_DAYS]
    return sorted(out, key=lambda r: r["last_contacted"])


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


def follow_ups(settings: Settings, args: dict) -> screen.Shown | str:
    due = due_rows(settings)
    if not due:
        return (f"Nobody is due a follow-up. A lead is due {FOLLOW_UP_DAYS} days after your first message if they "
                "haven't replied, and gets one follow-up at most.")
    rows = [[r["name"], where_(r), r.get("channel") or "-", st.short(day(r["last_contacted"])),
             f"{(st.today() - day(r['last_contacted'])).days} days"] for r in due]
    n = len(due)
    return st.table(f"{n} lead{'s are' if n != 1 else ' is'} due a follow-up: " + ", ".join(r["name"] for r in due[:5])
                    + (" and more" if n > 5 else "") + ". Each gets one polite follow-up at most; I'll draft them, "
                    "you send them.", "Due a follow-up", ["Lead", "Country", "Channel", "Messaged", "Since"], rows,
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
                        "One follow-up is the limit."}
    sent = day(row.get("last_contacted")) or st.today()
    waited = (st.today() - sent).days
    if waited < FOLLOW_UP_DAYS:
        return {"stop": f"You messaged {name} {waited} day{'s' if waited != 1 else ''} ago. Give them until "
                        f"{st.short(sent + timedelta(days=FOLLOW_UP_DAYS))} before a follow-up."}
    p = prospect or {}
    me = st.business(settings)
    country = world.country_code(args.get("country")) or row.get("country") or p.get("country") or world.HOME
    channel = args.get("channel") or row.get("channel") or row.get("draft_channel") or world.default_channel(country)
    if channel not in kinetic_sales.CHANNELS:
        raise ValueError("Which kind of message? " + ", ".join(kinetic_sales.CHANNELS) + ".")
    contact = st.clean(args.get("contact_name") or row.get("contact_name"), 40)
    hello = f"Hi {contact}," if contact else "Hi there,"
    sign = me["owner"] or "[your name]"
    first = {"email": "email", "letter": "letter", "dm": "message", "phone": "call", "visit": "visit"}.get(
        row.get("channel") or "", "message")
    offer = ("The free example home page I made for you is still yours to see, with no obligation."
             if args.get("mockup", True) else "I'd still be happy to share a few free ideas, with no obligation.")
    pr = kinetic_sales.prices(settings)
    start = world.local_price(pr["packages"]["starter"]["price"], world.currency_of(country))
    price = f"Websites start from {start}, and you pay {world.payment_terms(pr['deposit_percent'])}." \
        if args.get("price", True) else ""
    nudge = f"I'm just following up on my {first} from {st.short(sent)} about {name}'s website. I know how busy " \
            "running a business is, so I'll keep this short."
    bow_out = "If now isn't the right time, that's absolutely fine, and I won't chase you again."
    opt_out = world.OPT_OUT
    if channel == "email":
        address = me["address"] or ("[your postal address]" if world.rules_of(country) in ("us", "ca") else "")
        body = (f"Subject: Following up: {name}'s website\n\n{hello}\n\n{nudge}\n\n{offer}\n\n"
                + (f"{price}\n\n" if price else "") + f"{bow_out}\n\nThanks,\n{sign}\n{me['name']}"
                + "".join(f"\n{x}" for x in (me["phone"], me["website"], address) if x) + f"\n\n{opt_out}")
    elif channel == "letter":
        body = (f"{me['name']}\n{me['address'] or '[your address]'}\n{st.long_date(st.today())}\n\nTo the owner, {name}\n\n"
                f"{hello.replace('Hi', 'Dear')}\n\n{nudge}\n\n{offer}\n\n" + (f"{price}\n\n" if price else "") +
                f"{bow_out}\n\nYou can reach me on {me['phone'] or '[your phone]'} or {me['email'] or '[your email]'}.\n\n"
                f"Kind regards,\n{sign}\n\n{opt_out}")
    elif channel in ("phone", "visit"):
        body = (f"{'Phone' if channel == 'phone' else 'Walk-in'} follow-up script for {name}\n\n"
                f"1. \"Hi, it's {sign} from {me['name']}. I {'called' if first == 'call' else 'got in touch'} on "
                f"{st.short(sent)} about your website. Have you got a minute?\"\n2. \"{offer}\"\n"
                + (f"3. If they ask about price: \"{price}\"\n" if price else "") +
                f"{'4' if price else '3'}. \"{bow_out}\"\n"
                "This is the last time: if they say no or don't answer, thank them and leave it there.")
    else:
        body = (f"{hello} {nudge} {offer} " + (f"{price} " if price else "") + f"{bow_out} {sign}, {me['name']}"
                f"\n\n{opt_out}")
    return {"name": name, "channel": channel, "country": country,
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
    return st.text_card(f"I drafted a polite follow-up {channel} for {name}{said} and saved it in "
                        f"{st.where(settings, path)}. {st.NOT_SENT} It's their one follow-up; once you've sent it, tell "
                        "me and I'll leave them be unless they reply.", f"Follow-up: {name}", body, [
                            {"label": "Mark sent", "say": f"I sent the follow-up {channel} to {name}."},
                            {"label": "They replied", "say": f"{name} replied."}])


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
            + ", ".join(r["name"] for r in due[:3]) + (" and more" if n > 3 else "") +
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
        "description": "Kinetic Web Designs outreach tracker: who has been contacted and who is due a follow-up. "
                       "mark: record a lead's status when the user says so: contacted (\"I emailed Joe's Barbers\", "
                       "with channel and date if given), replied, interested, won, not interested, or opted out "
                       "(\"they said no thanks\"). Drafting a first message with web_design_sales outreach records "
                       "drafted by itself. leads: the list (filter by status or country). follow_ups: leads messaged "
                       f"{FOLLOW_UP_DAYS}+ days ago with no reply. follow_up: one polite follow-up draft in their "
                       "language; each lead gets at most one, two messages in all. summary: counts per status and per "
                       "country. Never draft for anyone opted out or not interested. Drafts only: never send "
                       "anything, and only mark a lead contacted when the user says they sent it.",
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
                "contact_name": {"type": "string", "description": "follow_up: the owner's first name if known."},
                "language": {"type": "string", "description": "follow_up: write it in this language; default the "
                                                              "lead's country's."},
                "price": {"type": "boolean", "description": "follow_up: mention the starting price (default true)."},
                "mockup": {"type": "boolean", "description": "follow_up: mention the free mock-up (default true)."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    if args.get("action") == "follow_up":  # async: it may ask Claude for a translation
        return await follow_up(settings, args)
    handlers = {"mark": mark, "leads": leads, "follow_ups": follow_ups, "follow_up": follow_up, "summary": summary}
    return await asyncio.to_thread(st.dispatch, handlers, args.get("action"), settings, args, "outreach tracker")
