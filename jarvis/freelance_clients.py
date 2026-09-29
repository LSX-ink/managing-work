"""Freelance clients and leads: client list with contact notes, a lead pipeline (enquiry, proposal sent, won, lost) with
win-rate stats, onboarding and offboarding checklists, feedback and testimonial request drafts and a testimonial bank.

Pop-ups: "freelance-board" (pipeline), "freelance-checklist", "freelance-calc" and tables. Contact notes are only kept on
this PC and nothing is ever sent. Data: freelance-clients.json, -leads.json, -checklists.json, -testimonials.json.
"""

from datetime import timedelta

import freelance_store as st
import screen
from config import Settings

NAMES = {"freelance_clients"}
STAGES = ["enquiry", "proposal sent", "won", "lost"]
ONBOARDING = [
    "Confirm scope, deliverables and price in writing", "Agree the timeline and key dates",
    "Send your terms or contract to be agreed", "Take the deposit or agree the payment schedule",
    "Ask for the brief, files and any logins (share them safely)", "Agree how and when you will keep in touch",
    "Set up the project folder and start time tracking", "Send a friendly welcome message",
    "Book a kickoff call or message", "Note how many rounds of changes are included",
]
OFFBOARDING = [
    "Deliver the final files and check them against the brief", "Send the final invoice",
    "Confirm all changes are closed", "Hand over source files, or say clearly they are not included",
    "Ask for feedback or a testimonial", "Ask if they know anyone else who needs help",
    "Ask permission to show the work in your portfolio", "Back up and archive the project files",
    "Remove your access to their accounts", "Note what went well and what to change next time",
    "Put a check-in for three months' time in your diary",
]
DRAFTS = ("feedback", "testimonial", "referral", "review")
ACTIONS = ["client_add", "client_note", "clients", "client_show", "client_remove", "client_value", "lead_add", "lead_move",
           "pipeline", "win_rate", "lead_followups", "followed_up", "onboarding", "offboarding", "feedback_draft", "testimonial_add",
           "testimonials"]


def _find_client(rows: list[dict], name) -> dict | None:
    key = st.find([c["name"] for c in rows], st.need(name, "client", 60))
    return next((c for c in rows if c["name"] == key), None)


def client_add(settings: Settings, args: dict) -> screen.Shown:
    rows = st.clients(settings)
    name = st.need(args.get("client"), "client", 60)
    if _find_client(rows, name) and _find_client(rows, name)["name"].lower() == name.lower():
        raise ValueError(f"{name} is already on your client list.")
    if len(rows) >= st.MAX_ROWS:
        raise ValueError("The client list is full.")
    rows.append({"name": name, "contact": st.clean(args.get("contact"), 120), "kind": st.clean(args.get("work"), 80),
                 "notes": [{"date": st.today().isoformat(), "text": st.clean(args.get("note"), 300)}] if args.get("note") else [],
                 "added": st.today().isoformat()})
    st.save(settings, st.CLIENTS, rows)
    return clients(settings, {}, f"Added {name}.")


def client_note(settings: Settings, args: dict) -> str:
    rows = st.clients(settings)
    hit = _find_client(rows, args.get("client"))
    if not hit:
        raise ValueError(f"I don't have a client called {st.clean(args.get('client'))}.")
    if args.get("contact"):
        hit["contact"] = st.clean(args["contact"], 120)
    if args.get("note"):
        hit["notes"].append({"date": st.today().isoformat(), "text": st.clean(args["note"], 300)})
    elif not args.get("contact"):
        raise ValueError("What should I note?")
    st.save(settings, st.CLIENTS, rows)
    return f"Noted for {hit['name']}."


def clients(settings: Settings, args: dict, prefix: str = "") -> screen.Shown:
    rows = st.clients(settings)
    if not rows:
        raise ValueError("No clients yet. Tell me who you work for.")
    table = [[c["name"], c["contact"] or "-", c["kind"] or "-", (c["notes"][-1]["text"][:60] if c["notes"] else "-")] for c in rows]
    return st.table(f"{prefix} You have {len(rows)} client{'s' if len(rows) != 1 else ''}.".strip(), "Freelance clients",
                    ["Client", "Contact", "Work", "Last note"], table)


def client_show(settings: Settings, args: dict) -> screen.Shown:
    hit = _find_client(st.clients(settings), args.get("client"))
    if not hit:
        raise ValueError(f"I don't have a client called {st.clean(args.get('client'))}.")
    hours = sum(e["hours"] for e in st.entries(settings, client=hit["name"]))
    projects = [p for p in st.projects(settings) if p["client"].lower() == hit["name"].lower()]
    leads = [x for x in st.rows_of(settings, st.LEADS) if x["client"].lower() == hit["name"].lower()]
    rows = [("Contact", hit["contact"] or "none saved"), ("Usual work", hit["kind"] or "-"), ("Since", hit["added"]),
            ("Projects", f"{len(projects)} ({sum(1 for p in projects if p['status'] != 'done')} open)"),
            ("Leads", str(len(leads))), ("Hours logged", st.num(round(hours, 2)))]
    notes = [f"{n['date']}: {n['text']}" for n in hit["notes"][-5:]]
    return st.calc(f"{hit['name']}: {len(projects)} projects, {st.num(round(hours, 2))} hours logged.", hit["name"], hit["name"],
                   hit["contact"], rows, notes or ["No notes yet."])


def client_remove(settings: Settings, args: dict) -> str:
    rows = st.clients(settings)
    hit = _find_client(rows, args.get("client"))
    if not hit:
        raise ValueError(f"I don't have a client called {st.clean(args.get('client'))}.")
    if not args.get("confirmed"):
        return f"Remove {hit['name']} and their notes from your client list? Say yes to confirm. Projects and time stay."
    rows.remove(hit)
    st.save(settings, st.CLIENTS, rows)
    return f"Removed {hit['name']}."


def client_value(settings: Settings, args: dict) -> screen.Shown:
    names = {c["name"] for c in st.clients(settings)} | {p["client"] for p in st.projects(settings)}
    if not names:
        raise ValueError("No clients or projects yet.")
    out = []
    for name in sorted(names):
        fees = sum(p.get("fee") or 0 for p in st.projects(settings) if p["client"].lower() == name.lower())
        hours = sum(e["hours"] for e in st.entries(settings, client=name))
        rate = f"{st.gbp(round(fees / hours, 2))}/h" if fees and hours else "-"
        out.append((fees, [name, st.gbp(fees), st.num(round(hours, 2)), rate]))
    out.sort(key=lambda r: -r[0])
    return st.table("Here is what each client has brought in against the time spent.", "Client value",
                    ["Client", "Project fees", "Hours", "Per hour"], [r for _, r in out],
                    [{"label": "Pipeline", "say": "Show my freelance pipeline."}])


def _leads(settings: Settings) -> list[dict]:
    return st.rows_of(settings, st.LEADS)


def lead_add(settings: Settings, args: dict) -> screen.Shown:
    rows = _leads(settings)
    if len(rows) >= st.MAX_ROWS:
        raise ValueError("The lead list is full.")
    stage = args.get("stage") or "enquiry"
    if stage not in STAGES:
        raise ValueError("A lead's stage is one of " + ", ".join(STAGES) + ".")
    follow = st.parse_date(args.get("follow_up"), "follow-up date")
    lead = {"id": st.next_id(rows), "client": st.client_name(settings, args.get("client")),
            "title": st.need(args.get("title"), "job", 80), "value": st.number(args.get("value"), "value", True) if args.get("value") is not None else 0.0,
            "stage": "enquiry", "source": st.clean(args.get("source"), 40), "date": st.today().isoformat(),
            "follow_up": (follow or st.today() + timedelta(days=3)).isoformat(), "lost_reason": "", "history": ["enquiry"]}
    rows.append(lead)
    st.save(settings, st.LEADS, rows)
    if stage != "enquiry":
        return lead_move(settings, {"lead_id": lead["id"], "stage": stage})
    return pipeline(settings, {}, f"Added lead {lead['id']}: {lead['title']}.")


def _lead(rows: list[dict], args: dict) -> dict:
    if args.get("lead_id") is not None:
        hit = next((x for x in rows if x["id"] == int(args["lead_id"])), None)
    else:
        name = st.need(args.get("client"), "lead number or client").lower()
        hits = [x for x in rows if name in x["client"].lower() and x["stage"] in ("enquiry", "proposal sent")]
        if len(hits) > 1:
            raise ValueError(f"{len(hits)} open leads for {args['client']}; give the lead number.")
        hit = hits[0] if hits else None
    if not hit:
        raise ValueError("I can't find that lead.")
    return hit


def lead_move(settings: Settings, args: dict) -> screen.Shown:
    rows = _leads(settings)
    lead = _lead(rows, args)
    stage = args.get("stage")
    if stage not in STAGES:
        raise ValueError("Move it to one of " + ", ".join(STAGES) + ".")
    lead["stage"] = stage
    lead["history"].append(stage)
    if args.get("value") is not None:
        lead["value"] = st.number(args["value"], "value", True)
    extra = ""
    if stage == "proposal sent":
        lead["follow_up"] = (st.today() + timedelta(days=7)).isoformat()
        extra = " I set a follow-up for a week's time."
    elif stage in ("won", "lost"):
        lead["follow_up"] = ""
    if stage == "lost":
        lead["lost_reason"] = st.clean(args.get("reason"), 100)
    if stage == "won" and not any(c["name"].lower() == lead["client"].lower() for c in st.clients(settings)):
        people = st.clients(settings)
        people.append({"name": lead["client"], "contact": "", "kind": "", "notes": [], "added": st.today().isoformat()})
        st.save(settings, st.CLIENTS, people)
        extra += f" {lead['client']} is now on your client list."
    st.save(settings, st.LEADS, rows)
    return pipeline(settings, {}, f"Lead {lead['id']} is now {stage}.{extra}")


def pipeline(settings: Settings, args: dict, prefix: str = "") -> screen.Shown:
    rows = _leads(settings)
    if not rows:
        raise ValueError("No leads yet. Tell me about an enquiry.")
    cols = []
    for stage in STAGES:
        items = [x for x in rows if x["stage"] == stage]
        nxt = STAGES[STAGES.index(stage) + 1] if stage in ("enquiry", "proposal sent") else ""
        cards = [{"id": x["id"], "title": x["title"], "client": x["client"], "value": st.gbp(x["value"]) if x["value"] else "",
                  "follow": x["follow_up"], "say": f"Move lead {x['id']} to {nxt}." if nxt else f"Tell me about lead {x['id']}."}
                 for x in items[-12:]]
        cols.append({"stage": stage, "count": len(items), "value": st.gbp(sum(x["value"] for x in items)), "cards": cards})
    open_value = sum(x["value"] for x in rows if x["stage"] in ("enquiry", "proposal sent"))
    return screen.Shown(f"{prefix} {sum(1 for x in rows if x['stage'] in ('enquiry', 'proposal sent'))} open leads worth {st.gbp(open_value)}, "
                        "which is hope rather than income.".strip(), screen.card(
        st.BOARD, "Freelance pipeline", "freelance-pipeline", data={"columns": cols, "note": "Values are what you hope to win, not promised income."},
        buttons=[{"label": "Win rate", "say": "What's my freelance win rate?"}]))


def win_rate(settings: Settings, args: dict) -> screen.Shown:
    rows = _leads(settings)
    won = [x for x in rows if x["stage"] == "won"]
    lost = [x for x in rows if x["stage"] == "lost"]
    if not won and not lost:
        raise ValueError("Win rate needs at least one won or lost lead.")
    sent = [x for x in rows if "proposal sent" in x["history"]]
    rate = round(100 * len(won) / (len(won) + len(lost)))
    stats = [("Won", str(len(won))), ("Lost", str(len(lost))), ("Open", str(len(rows) - len(won) - len(lost))),
             ("Proposals sent", str(len(sent))),
             ("Average won job", st.gbp(round(sum(x["value"] for x in won) / len(won), 2)) if won else "-")]
    sources: dict[str, list[int]] = {}
    for x in won + lost:
        sources.setdefault(x["source"] or "unknown", [0, 0])[0 if x["stage"] == "won" else 1] += 1
    for name, (w, lo) in sorted(sources.items()):
        stats.append((f"From {name}", f"{w} won of {w + lo}"))
    reasons = [x["lost_reason"] for x in lost if x["lost_reason"]]
    notes = ["Small numbers swing a lot, so treat this as a rough guide.", "Lost reasons: " + "; ".join(reasons[-5:])] if reasons \
        else ["Small numbers swing a lot, so treat this as a rough guide."]
    return st.calc(f"You have won {len(won)} of {len(won) + len(lost)} decided leads, {rate}%.", "Win rate", f"{rate}% won",
                   "won out of won plus lost", stats, notes)


def lead_followups(settings: Settings, args: dict) -> screen.Shown:
    horizon = st.today() + timedelta(days=int(args.get("days") or 0))
    due = sorted((x for x in _leads(settings) if x["follow_up"] and x["stage"] in ("enquiry", "proposal sent")
                  and st.parse_date(x["follow_up"]) <= horizon), key=lambda x: x["follow_up"])
    if not due:
        return "No leads need a follow-up."
    items = [{"label": f"{x['client']}: {x['title']} ({st.until(st.parse_date(x['follow_up']))})",
              "say": f"I've followed up on lead {x['id']}. Set the next follow-up for a week's time."} for x in due]
    return screen.Shown(f"{len(due)} lead{'s' if len(due) != 1 else ''} to chase.", screen.card("list", "Leads to chase", "freelance-chase", items=items))


def followed_up(settings: Settings, args: dict) -> str:
    rows = _leads(settings)
    lead = _lead(rows, args)
    lead["follow_up"] = (st.today() + timedelta(days=7)).isoformat()
    st.save(settings, st.LEADS, rows)
    return f"Noted. I'll nudge you about {lead['client']} again in a week."


def _checklist(settings: Settings, args: dict, kind: str, items: list[str]) -> screen.Shown:
    client = st.client_name(settings, args.get("client"))
    key = f"{kind}|{client.lower()}"
    ticks = st.load(settings, st.CHECKLISTS, {})
    done = set(ticks.get(key, []))
    for arg, add in (("tick", True), ("untick", False)):
        if args.get(arg) is not None:
            n = int(args[arg])
            if not 1 <= n <= len(items):
                raise ValueError(f"The {kind} list has {len(items)} steps.")
            (done.add if add else done.discard)(n - 1)
    ticks[key] = sorted(done)
    st.save(settings, st.CHECKLISTS, ticks)
    rows = [{"text": t, "done": i in done, "say": f"{'Untick' if i in done else 'Tick'} step {i + 1} of the {kind} list for {client}."}
            for i, t in enumerate(items)]
    return screen.Shown(f"{client} {kind}: {len(done)} of {len(items)} steps done.", screen.card(
        st.CHECK, f"{kind.title()}: {client}", f"freelance-{kind}-{client.lower()}", data={
            "items": rows, "done": len(done), "total": len(items), "note": "Click a step to tick it."}))


def onboarding(settings: Settings, args: dict) -> screen.Shown:
    return _checklist(settings, args, "onboarding", ONBOARDING)


def offboarding(settings: Settings, args: dict) -> screen.Shown:
    return _checklist(settings, args, "offboarding", OFFBOARDING)


def _sign(args: dict) -> str:
    return st.clean(args.get("my_name"), 40) or "[Your name]"


def feedback_draft(settings: Settings, args: dict) -> screen.Shown:
    kind = args.get("kind") or "testimonial"
    if kind not in DRAFTS:
        raise ValueError("A draft is one of " + ", ".join(DRAFTS) + ".")
    client = st.client_name(settings, args.get("client"))
    who = st.clean(args.get("contact_name"), 40) or client
    project = st.clean(args.get("project"), 80) or "our project together"
    bodies = {
        "feedback": f"Hi {who},\n\nThanks again for working with me on {project}. I'm always trying to improve, so I'd really value "
                    "your honest feedback. Two quick questions:\n\n1. What worked well?\n2. What could I have done better?\n\n"
                    "A few lines is plenty.",
        "testimonial": f"Hi {who},\n\nI really enjoyed working on {project} with you. If you're happy with how it went, would you be "
                       "willing to write a couple of sentences I could share as a testimonial? It helps a lot.\n\nIt might cover what "
                       "you needed, what it was like to work with me, and the result. I will only use it if you say I can, and I'm happy "
                       "to change the wording.",
        "referral": f"Hi {who},\n\nThanks for the chance to work on {project}. If you know anyone who could use similar help, I'd be "
                    "grateful for an introduction. No pressure at all.",
        "review": f"Hi {who},\n\nThanks for choosing me for {project}. If you were happy with it, a short review on the site where "
                  "we worked together would mean a lot. Please only leave it if you feel it's deserved.",
    }
    body = bodies[kind] + f"\n\nThanks,\n{_sign(args)}"
    return st.draft(settings, f"{kind.title()} request: {client}", body, f"Here is a {kind} request for {client}.",
                    f"{kind.title()} request - {st.slug(client)}")


def testimonial_add(settings: Settings, args: dict) -> screen.Shown:
    rows = st.rows_of(settings, st.TESTIMONIALS)
    if len(rows) >= st.MAX_ROWS:
        raise ValueError("The testimonial bank is full.")
    rows.append({"id": st.next_id(rows), "client": st.client_name(settings, args.get("client")),
                 "quote": st.need(args.get("quote"), "quote", 600), "project": st.clean(args.get("project"), 80),
                 "permission": bool(args.get("permission")), "date": st.today().isoformat()})
    st.save(settings, st.TESTIMONIALS, rows)
    return testimonials(settings, {}, "Saved it.")


def testimonials(settings: Settings, args: dict, prefix: str = "") -> screen.Shown:
    rows = st.rows_of(settings, st.TESTIMONIALS)
    if args.get("approved_only"):
        rows = [r for r in rows if r["permission"]]
    if not rows:
        raise ValueError("No testimonials saved yet.")
    table = [[str(r["id"]), r["client"], r["quote"][:90], "yes" if r["permission"] else "not yet", r["project"] or "-"] for r in rows]
    return st.table(f"{prefix} {len(rows)} testimonial{'s' if len(rows) != 1 else ''} in your bank. Only publish ones the client has said you can use.".strip(),
                    "Testimonial bank", ["#", "Client", "Quote", "OK to use", "Project"], table)


def tool_definitions() -> list[dict]:
    return [{
        "name": "freelance_clients",
        "description": "Freelance clients and leads: add clients with contact notes, lead pipeline (enquiry, proposal sent, won, lost), "
                       "win rate, leads to chase, client onboarding and offboarding checklists, feedback / testimonial / referral / review "
                       "request drafts, testimonial bank. Drafts only, nothing is sent. remove needs confirmed true after the user says yes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "client": {"type": "string"}, "contact": {"type": "string", "description": "Email, phone or how to reach them (kept on this PC)."},
                "contact_name": {"type": "string", "description": "Person's first name for a draft."},
                "work": {"type": "string", "description": "Usual kind of work."}, "note": {"type": "string"},
                "title": {"type": "string", "description": "Lead: the job."}, "value": {"type": "number"},
                "stage": {"type": "string", "enum": STAGES}, "source": {"type": "string", "description": "Where the lead came from."},
                "lead_id": {"type": "integer"}, "reason": {"type": "string", "description": "Why a lead was lost."},
                "follow_up": {"type": "string", "description": "YYYY-MM-DD, today or tomorrow."},
                "days": {"type": "integer", "description": "lead_followups: also include ones due within this many days."},
                "tick": {"type": "integer", "description": "Checklist step number to tick."},
                "untick": {"type": "integer", "description": "Checklist step number to untick."},
                "kind": {"type": "string", "enum": list(DRAFTS)}, "project": {"type": "string"},
                "my_name": {"type": "string"}, "quote": {"type": "string"},
                "permission": {"type": "boolean", "description": "True only if the client said the quote may be used."},
                "approved_only": {"type": "boolean"},
                "confirmed": {"type": "boolean", "description": "Set true only after the user confirms a removal."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"client_add": client_add, "client_note": client_note, "clients": clients, "client_show": client_show,
                "client_remove": client_remove, "client_value": client_value, "lead_add": lead_add, "lead_move": lead_move,
                "pipeline": pipeline, "win_rate": win_rate, "lead_followups": lead_followups, "followed_up": followed_up, "onboarding": onboarding,
                "offboarding": offboarding, "feedback_draft": feedback_draft, "testimonial_add": testimonial_add,
                "testimonials": testimonials}
    return st.dispatch(handlers, args.get("action"), settings, args, "freelance client")
