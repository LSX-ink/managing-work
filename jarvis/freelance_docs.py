"""Freelance paperwork: proposal and quote builder, portfolio case-study builder (both saved as Markdown or HTML files),
standard terms, kickoff questions, welcome and follow-up drafts, a profile bio, plain-words checklists for Fiverr and
Upwork-style sites, and what a platform's fee leaves you.

Files go in the "Freelance" folder of the memory folder. Drafts are never sent, and terms are general wording, not legal
advice. Checklists pop up as "freelance-checklist". Data: freelance-checklists.json.
"""

from html import escape

import freelance_store as st
import memory
import screen
from config import Settings

NAMES = {"freelance_docs"}
FORMATS = ["md", "html"]
SERVICES = ["design", "editing", "writing", "video editing", "virtual assistant", "other"]
PLATFORMS = ["general", "fiverr", "upwork", "peopleperhour", "freelancer"]
ACTIONS = ["proposal", "case_study", "terms_draft", "kickoff_questions", "welcome_draft", "proposal_followup", "profile_bio",
           "platform_checklist", "platform_tick", "platform_net", "files"]
LEGAL = "General wording only, not legal advice. For bigger jobs, have a solicitor or your professional body check it."

QUESTIONS = {
    "design": ["What is the project for and who is it aimed at?", "What should people think, feel or do when they see it?",
               "Which brand colours, fonts and logos must I use?", "Which designs do you like or dislike, and why?",
               "What sizes and file types do you need?", "Who signs it off, and by when?"],
    "editing": ["Where are the source files, and how will you share them?", "How long should the finished piece be?",
                "Where will it be published and in what format?", "Can you share examples of the style you like?",
                "Do you have music, logos or captions to include?", "Who approves the final cut, and by when?"],
    "writing": ["Who is the reader and what should they do afterwards?", "What is the topic, angle and word count?",
                "What tone of voice should it have, with examples?", "Do you have sources, interviews or notes to use?",
                "Are there keywords, links or words to avoid?", "Who edits and approves it, and by when?"],
    "video editing": ["How long is the raw footage, and how will you send it?", "What length, ratio and platform is the final video for?",
                      "Which style or channels are the reference?", "Do you need captions, music, graphics or colour work?",
                      "How many rounds of changes are included?", "When do you need the first cut and the final one?"],
    "virtual assistant": ["Which tasks do you want handed over first?", "Which tools and accounts will I need access to?",
                          "How many hours a week or month, and on which days?", "How should we communicate and how fast do you expect replies?",
                          "What are the rules for anything sensitive or private?", "How will we review how it is going?"],
    "other": ["What do you want to end up with?", "Why now, and what is the deadline?", "Who else is involved in decisions?",
              "What has been tried before?", "What budget have you set aside?", "How will we both know it has gone well?"],
}
CHECKLISTS = {
    "general": ["A clear photo of your face or logo", "A headline saying what you do and for whom, in plain words",
                "A short description that starts with the client's problem, not your life story", "Three to five samples of your best work",
                "A price or price range you are happy with, including the site's fee", "Your working hours and how fast you reply",
                "Your skills and tools, only ones you really have", "A short note on how you work, with steps and changes included",
                "Read the site's rules on fees, contact outside the site and getting paid", "Ask past clients for reviews, honestly and with permission"],
    "fiverr": ["A gig title that says exactly what the buyer gets", "Three packages (basic, standard, premium) with clear differences",
               "Delivery time you can keep, with spare days", "A gallery of good samples, with a short video if it suits", "A short FAQ answering the usual questions",
               "Add-ons such as fast delivery or extra changes", "A description that says what is and is not included",
               "A friendly instant reply for new messages", "Check the site's help pages for its current fee and rules"],
    "upwork": ["A profile title that names your speciality", "An overview that opens with the client's problem", "A portfolio with a few projects and results",
               "Skills and categories that match the jobs you want", "An hourly rate you have worked out, not guessed", "A proposal template you personalise every time",
               "Read each job post fully and answer its questions", "Ask a smart question in every proposal", "Check the site's help pages for fees and how bids work"],
    "peopleperhour": ["A profile headline and photo", "Your speciality, in one sentence", "Fixed-price offers with clear deliverables", "Samples in a portfolio",
                      "Reply quickly and politely", "Check the site's help pages for fees and payment protection"],
    "freelancer": ["A profile headline and photo", "Your skills and a short summary", "A portfolio of your best work", "Bids that address the brief",
                   "A price and timeline you can keep", "Check the site's help pages for fees and how contests and bids work"],
}


def _md(title: str, sections: list) -> str:
    out = [f"# {title}", ""]
    for heading, blocks in sections:
        out += [f"## {heading}", ""]
        for b in blocks:
            if isinstance(b, str):
                out += [b, ""]
            elif b[0] == "ul":
                out += [f"- {x}" for x in b[1]] + [""]
            else:
                out += ["| " + " | ".join(b[1]) + " |", "|" + " --- |" * len(b[1])] + ["| " + " | ".join(r) + " |" for r in b[2]] + [""]
    return "\n".join(out).rstrip() + "\n"


def _html(title: str, sections: list) -> str:
    body = [f"<h1>{escape(title)}</h1>"]
    for heading, blocks in sections:
        body.append(f"<h2>{escape(heading)}</h2>")
        for b in blocks:
            if isinstance(b, str):
                body.append(f"<p>{escape(b)}</p>")
            elif b[0] == "ul":
                body.append("<ul>" + "".join(f"<li>{escape(x)}</li>" for x in b[1]) + "</ul>")
            else:
                head = "".join(f"<th>{escape(h)}</th>" for h in b[1])
                rows = "".join("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in r) + "</tr>" for r in b[2])
                body.append(f"<table><tr>{head}</tr>{rows}</table>")
    style = ("body{font-family:Georgia,serif;max-width:720px;margin:2em auto;padding:0 1em;color:#111;line-height:1.5}"
             "table{border-collapse:collapse;width:100%}th,td{border:1px solid #999;padding:6px;text-align:left}h1,h2{font-family:Arial,sans-serif}")
    return (f"<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><title>{escape(title)}</title>"
            f"<style>{style}</style></head><body>\n" + "\n".join(body) + "\n</body></html>\n")


def _save(settings: Settings, title: str, sections: list, args: dict, said: str) -> screen.Shown:
    fmt = args.get("format") or "md"
    if fmt not in FORMATS:
        raise ValueError("The format is md or html.")
    text = _md(title, sections) if fmt == "md" else _html(title, sections)
    path = st.write_file(settings, f"{title}.{fmt}", text)
    return st.file_shown(settings, path, f"{said} Saved as {path.name} in the Freelance folder. Nothing has been sent.")


def _list(value, limit: int = 15) -> list[str]:
    items = [st.clean(x, 200) for x in (value or []) if st.clean(x)]
    return items[:limit]


def proposal(settings: Settings, args: dict) -> screen.Shown:
    client = st.client_name(settings, args.get("client"))
    name = st.need(args.get("title"), "project title", 60)
    scope, deliverables = _list(args.get("scope")), _list(args.get("deliverables"))
    if not scope or not deliverables:
        raise ValueError("Give me the scope and the deliverables, as short lists.")
    steps = _list(args.get("timeline"))
    opts = [o for o in args.get("options") or [] if isinstance(o, dict) and o.get("name")]
    if opts:
        prices = [[st.clean(o["name"], 40), st.gbp(st.number(o.get("price"), "option price")), st.clean(o.get("includes"), 160) or "-"] for o in opts[:4]]
        money = [("table", ["Option", "Price", "Includes"], prices)]
    else:
        money = [f"Fixed price: {st.gbp(st.number(args.get('price'), 'price'))}."]
    rounds = int(args["revision_rounds"]) if args.get("revision_rounds") is not None else 2
    days = int(args.get("terms_days") or 14)
    valid = int(args.get("valid_days") or 14)
    dep = st.number(args["deposit_pct"], "deposit", True, 100) if args.get("deposit_pct") is not None else 30.0
    terms = [f"A {st.num(dep)}% deposit is due before work starts; the rest is invoiced on delivery and due within {days} days." if dep
             else f"Invoiced on delivery and due within {days} days.",
             f"The price includes {rounds} rounds of changes. Extra changes or new requests are quoted separately.",
             "Rights in the finished work pass to you once the final invoice is paid.",
             "Late payment: statutory interest and fixed costs may be added under UK law where it applies.",
             f"This proposal is valid for {valid} days from {st.long_date(st.today())}."]
    sections = [("Summary", [st.clean(args.get("summary"), 500) or f"A proposal for {client}: {name}."]),
                ("Scope", [("ul", scope)]), ("Deliverables", [("ul", deliverables)])]
    if args.get("exclusions"):
        sections.append(("Not included", [("ul", _list(args["exclusions"]))]))
    if steps:
        sections.append(("Timeline", [("ul", steps)]))
    sections += [("Price", money), ("Terms", [("ul", terms)]),
                 ("Next steps", ["Reply to say yes and choose an option, and I'll send the deposit invoice and book the start date.",
                                 st.clean(args.get("my_name"), 40) or "[Your name]"])]
    return _save(settings, f"Proposal - {st.slug(client)} - {st.slug(name)}", sections, args, f"Your proposal for {client} is ready.")


def case_study(settings: Settings, args: dict) -> screen.Shown:
    name = st.need(args.get("title"), "case study title", 80)
    problem, result = st.need(args.get("problem"), "problem", 500), st.need(args.get("result"), "result", 500)
    process = _list(args.get("process"))
    if not process:
        raise ValueError("Give me the steps of your process, as a short list.")
    sections = [("The problem", [problem]), ("My process", [("ul", process)]), ("The result", [result])]
    if args.get("numbers"):
        sections[-1][1].append(("ul", _list(args["numbers"])))
    if args.get("quote"):
        sections.append(("What the client said", [f"\"{st.clean(args['quote'], 400)}\"" + (f" - {st.clean(args.get('client'), 60)}" if args.get("client") else "")]))
    if args.get("tools"):
        sections.append(("Tools", [("ul", _list(args["tools"]))]))
    return _save(settings, f"Case study - {st.slug(name)}", sections, args,
                 "Your case study is ready. Only use real numbers and quotes, and ask the client before naming them.")


def terms_draft(settings: Settings, args: dict) -> screen.Shown:
    days = int(args.get("terms_days") or 14)
    dep = st.number(args["deposit_pct"], "deposit", True, 100) if args.get("deposit_pct") is not None else 30.0
    rounds = int(args["revision_rounds"]) if args.get("revision_rounds") is not None else 2
    kill = st.number(args["cancel_pct"], "cancellation fee", True, 100) if args.get("cancel_pct") is not None else 30.0
    sections = [("About these terms", [LEGAL]),
                ("Payment", [("ul", [f"A {st.num(dep)}% deposit is paid before work begins.", f"Invoices are due within {days} days.",
                                     "Late payment may carry statutory interest and fixed costs where UK law allows it."])]),
                ("Changes", [("ul", [f"The price includes {rounds} rounds of changes.", "Anything outside the agreed scope is quoted separately before I start it."])]),
                ("Ownership", [("ul", ["You own the final work once it is paid in full.", "I may show it in my portfolio unless you ask me not to."])]),
                ("Your materials and privacy", [("ul", ["You confirm you have the right to use anything you send me.", "I keep your information private and use it only for the job."])]),
                ("Cancelling", [("ul", [f"If you cancel after work has started, I may keep {st.num(kill)}% of the price, or payment for work done, whichever is more.",
                                        "If I can't finish, I'll refund payment for work not delivered."])]),
                ("Responsibility", [("ul", ["I'll take reasonable care and skill.", "Delays caused by late feedback or materials move the deadline."])])]
    return _save(settings, "Freelance terms", sections, args, "Here is a plain draft of your terms.")


def kickoff_questions(settings: Settings, args: dict) -> screen.Shown:
    service = args.get("service") or "other"
    if service not in SERVICES:
        raise ValueError("The service is one of " + ", ".join(SERVICES) + ".")
    body = f"Kickoff questions ({service})\n\n" + "\n".join(f"{i}. {q}" for i, q in enumerate(QUESTIONS[service], 1))
    return st.draft(settings, f"Kickoff questions: {service}", body, f"Here are {len(QUESTIONS[service])} kickoff questions for a {service} job.",
                    f"Kickoff questions - {service}")


def welcome_draft(settings: Settings, args: dict) -> screen.Shown:
    client = st.client_name(settings, args.get("client"))
    who = st.clean(args.get("contact_name"), 40) or client
    project = st.clean(args.get("project"), 80) or "the project"
    start = st.parse_date(args.get("start"), "start date")
    body = (f"Hi {who},\n\nThanks for choosing me for {project}. I'm looking forward to it.\n\nHere's how it will work:\n"
            + (f"- I'll start on {st.long_date(start)}.\n" if start else "- I'll confirm the start date once the deposit is in.\n")
            + "- I'll send updates at each stage, and you can reach me here any weekday.\n- Please send the brief, files and any logins as soon as you can.\n"
              "- I'll send the deposit invoice and terms in a separate message.\n\nIs there a good time this week for a short kickoff call?\n\nThanks,\n"
            + (st.clean(args.get("my_name"), 40) or "[Your name]"))
    return st.draft(settings, f"Welcome: {client}", body, f"Here is a welcome message for {client}.", f"Welcome - {st.slug(client)}")


def proposal_followup(settings: Settings, args: dict) -> screen.Shown:
    client = st.client_name(settings, args.get("client"))
    who = st.clean(args.get("contact_name"), 40) or client
    project = st.clean(args.get("project"), 80) or "the project"
    body = (f"Hi {who},\n\nI hope you're well. I wanted to check in on the proposal I sent for {project}. Have you had a chance to look?\n\n"
            "I'm happy to answer questions, adjust the scope or talk through the options. If the timing has changed, that's fine too, "
            f"just let me know.\n\nThanks,\n{st.clean(args.get('my_name'), 40) or '[Your name]'}")
    return st.draft(settings, f"Proposal follow-up: {client}", body, f"Here is a friendly follow-up for {client}.", f"Follow-up - {st.slug(client)}")


def profile_bio(settings: Settings, args: dict) -> screen.Shown:
    service = st.need(args.get("service"), "service", 60)
    who = st.clean(args.get("audience"), 80) or "small businesses and creators"
    proof = _list(args.get("proof"), 5)
    headline = f"{service.capitalize()} for {who}"
    lines = [f"Headline: {headline}", "", f"Bio: I help {who} with {service}. Working with me means clear communication, work delivered "
             "on time, and changes handled fairly."]
    lines += ["", "Proof to mention (only what is true):"] + [f"- {p}" for p in proof] if proof else ["", "Add one or two true results or client examples."]
    lines += ["", "How I work: 1. We agree scope and price. 2. I share a first version. 3. We refine it. 4. I deliver final files.",
              "", "Keep it honest: only claim work and results you can show."]
    return st.draft(settings, "Profile bio", "\n".join(lines), "Here is a starter headline and bio.", "Profile bio")


def platform_checklist(settings: Settings, args: dict) -> screen.Shown:
    platform = args.get("platform") or "general"
    if platform not in PLATFORMS:
        raise ValueError("The platform is one of " + ", ".join(PLATFORMS) + ".")
    items = CHECKLISTS[platform]
    key = f"platform|{platform}"
    ticks = st.load(settings, st.CHECKLISTS, {})
    done = set(ticks.get(key, []))
    for arg, add in (("tick", True), ("untick", False)):
        if args.get(arg) is not None:
            n = int(args[arg])
            if not 1 <= n <= len(items):
                raise ValueError(f"That checklist has {len(items)} steps.")
            (done.add if add else done.discard)(n - 1)
    ticks[key] = sorted(done)
    st.save(settings, st.CHECKLISTS, ticks)
    rows = [{"text": t, "done": i in done, "say": f"{'Untick' if i in done else 'Tick'} step {i + 1} of my {platform} profile checklist."}
            for i, t in enumerate(items)]
    return screen.Shown(f"{platform.title()} profile: {len(done)} of {len(items)} steps done.", screen.card(
        st.CHECK, f"{platform.title()} profile checklist", f"freelance-platform-{platform}", data={
            "items": rows, "done": len(done), "total": len(items),
            "note": "Plain-words advice only. Sites change their rules and fees, so check their own help pages."}))


def platform_tick(settings: Settings, args: dict) -> screen.Shown:
    if args.get("tick") is None and args.get("untick") is None:
        raise ValueError("Which step number should I tick?")
    return platform_checklist(settings, args)


def platform_net(settings: Settings, args: dict) -> screen.Shown:
    price = st.number(args.get("price"), "price")
    fee = st.number(args.get("fee_pct"), "the site's fee percentage", True, 90)
    other = st.number(args["costs"], "costs", True) if args.get("costs") is not None else 0.0
    net = round(price * (1 - fee / 100) - other, 2)
    rows = [("Price", st.gbp(price)), (f"Site fee {st.num(fee)}%", st.gbp(round(price * fee / 100, 2))), ("Other costs", st.gbp(other)), ("You keep", st.gbp(net))]
    if args.get("hours"):
        rows.append(("Per hour", st.gbp(round(net / st.number(args["hours"], "hours"), 2))))
    return st.calc(f"After the site's {st.num(fee)}% fee you would keep {st.gbp(net)}.", "What the platform leaves you", st.gbp(net), "after fees and costs",
                   rows, ["Use the fee percentage from the site's own help pages, as it can change.", st.HONEST])


def files(settings: Settings, args: dict) -> screen.Shown:
    folder = memory.root(settings) / st.FOLDER
    found = sorted((p for p in folder.glob("*") if p.is_file()), key=lambda p: -p.stat().st_mtime) if folder.exists() else []
    if not found:
        return "There are no freelance files yet. Ask me for a proposal or a case study."
    items = [{"label": p.name, "say": f"Show the file {p.name} in the Freelance folder."} for p in found[:60]]
    return screen.Shown(f"{len(found)} freelance file{'s' if len(found) != 1 else ''} saved.", screen.card("list", "Freelance files", "freelance-files", items=items))


def tool_definitions() -> list[dict]:
    text_list = {"type": "array", "items": {"type": "string"}}
    option = {"type": "object", "properties": {"name": {"type": "string"}, "price": {"type": "number"}, "includes": {"type": "string"}},
              "required": ["name", "price"], "additionalProperties": False}
    return [{
        "name": "freelance_docs",
        "description": "Freelance paperwork saved as files: proposal / quote (scope, deliverables, timeline, price options, terms) as Markdown "
                       "or HTML, portfolio case study (problem, process, result), standard terms, kickoff questions, welcome message, proposal "
                       "follow-up, profile bio, Fiverr / Upwork-style profile checklist with ticks, what a platform fee leaves you, list files. "
                       "Drafts only; nothing is sent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "client": {"type": "string"}, "contact_name": {"type": "string"}, "my_name": {"type": "string"},
                "title": {"type": "string", "description": "Project or case study title."}, "project": {"type": "string"},
                "summary": {"type": "string"}, "scope": text_list, "deliverables": text_list, "exclusions": text_list,
                "timeline": text_list, "price": {"type": "number"}, "options": {"type": "array", "items": option, "description": "Price options."},
                "revision_rounds": {"type": "integer"}, "deposit_pct": {"type": "number"}, "terms_days": {"type": "integer"},
                "valid_days": {"type": "integer"}, "cancel_pct": {"type": "number"},
                "format": {"type": "string", "enum": FORMATS},
                "problem": {"type": "string"}, "process": text_list, "result": {"type": "string"}, "numbers": text_list,
                "quote": {"type": "string"}, "tools": text_list,
                "service": {"type": "string", "description": "design, editing, writing, video editing, virtual assistant, other; or what the user offers."},
                "audience": {"type": "string"}, "proof": text_list, "start": {"type": "string", "description": "YYYY-MM-DD."},
                "platform": {"type": "string", "enum": PLATFORMS}, "tick": {"type": "integer"}, "untick": {"type": "integer"},
                "fee_pct": {"type": "number", "description": "The site's fee percentage, from the user."}, "costs": {"type": "number"},
                "hours": {"type": "number"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"proposal": proposal, "case_study": case_study, "terms_draft": terms_draft, "kickoff_questions": kickoff_questions,
                "welcome_draft": welcome_draft, "proposal_followup": proposal_followup, "profile_bio": profile_bio,
                "platform_checklist": platform_checklist, "platform_tick": platform_tick, "platform_net": platform_net, "files": files}
    return st.dispatch(handlers, args.get("action"), settings, args, "freelance document")
