"""Newsletter planner: issue calendar, section templates, subject line ideas and checker, subscriber and open-rate logs,
welcome email drafts, lead magnet ideas and a before-you-send checklist.

Data is in writingincome-newsletter.json in the memory folder. The subscriber and open numbers are typed by you; nothing is
sent and no email service is contacted. Results pop up as tables, charts and writingincome-* cards (frontend/popup-writingincome.js).
"""

import re
from datetime import timedelta

import screen
import writingincome_store as wi
from config import Settings

NAMES = {"writingincome_newsletter"}
STATUSES = ["idea", "drafting", "ready", "sent"]
SPAM = ["free", "guarantee", "guaranteed", "act now", "winner", "cash", "urgent", "click here", "make money", "earn money", "risk-free",
        "100%", "limited time", "buy now", "no obligation", "congratulations"]

TEMPLATES = {
    "digest": ("Curated digest", ["Opening line: one sentence on the theme of the week", "Top pick: the one thing worth their time, and why",
                                  "Three quick links, each with one line of your opinion", "One thing you learned or made this week",
                                  "Sign-off: a question they can reply to"]),
    "essay": ("Single essay", ["Hook: a scene, a surprise or a question", "The problem, in the reader's words", "Your story or example",
                               "The idea or lesson, in plain words", "What they can try this week", "Sign-off with one reply prompt"]),
    "tips": ("Tips and how-to", ["Short intro: who this helps and what they will be able to do", "Step-by-step (three to five steps)",
                                 "A common mistake to avoid", "A tool, template or checklist", "Next issue teaser"]),
    "personal": ("Personal update", ["What happened this month, honestly", "What you are working on now", "One thing that helped",
                                     "One thing you would like readers to tell you", "Thanks and a small ask"]),
}
LEAD_MAGNETS = [
    ("Checklist", "one page they can tick off", "low"), ("Cheat sheet", "the key facts of your topic on one page", "low"),
    ("Template", "a ready-to-fill document or spreadsheet", "low"), ("Mini guide", "a 5 to 10 page PDF that solves one problem", "medium"),
    ("Swipe file", "a collection of your best examples with notes", "medium"), ("Email mini-course", "3 to 5 short lessons over several days",
                                                                             "medium"),
    ("Reading list", "your favourite books or articles with a line on each", "low"), ("Resource library", "links and tools you use", "medium"),
    ("Workbook", "prompts and exercises to fill in", "medium"), ("Quiz or self-check", "a short questionnaire with advice for each result",
                                                                 "high"),
    ("Sample chapter", "the first chapter of your book or a piece of your writing", "low"), ("Planner printable", "a weekly or monthly planner page", "medium"),
]
WELCOME = [
    (0, "Welcome, and here is your {gift}", "Say thanks, deliver the lead magnet and set expectations.",
     "Hi [first name],\n\nThanks for joining [newsletter name]. Here is [lead magnet link].\n\nEach [day] I send [what they get]. It takes about "
     "[minutes] minutes to read.\n\nTo start, reply and tell me [one easy question]. I read every reply.\n\n[Your name]"),
    (2, "Why I write this", "A short personal story that shows who you are and why you care.",
     "Hi [first name],\n\nA quick story about why I started [newsletter name]: [two or three sentences].\n\nThe idea behind it: [one sentence].\n\n"
     "If that sounds like you, you are in the right place.\n\n[Your name]"),
    (4, "My three most useful posts", "Point to your best existing work so new readers see the value fast.",
     "Hi [first name],\n\nIf you read only three things I have written, make them these:\n\n1. [title and link], for [who it helps]\n"
     "2. [title and link]\n3. [title and link]\n\nTell me which one helped most.\n\n[Your name]"),
    (7, "One question for you", "Ask what they want, so you can write what they need.",
     "Hi [first name],\n\nYou have had a week of [newsletter name]. What is the one thing you would like help with?\n\nJust hit reply. I "
     "will use your answers to plan future issues.\n\n[Your name]"),
    (10, "What is coming next", "Tell them what to expect and, if relevant, mention anything you sell honestly.",
     "Hi [first name],\n\nHere is what is coming: [next topics].\n\n[Optional: one honest line about anything you offer, with the "
     "affiliate or sponsor disclosure if there is one.]\n\nThanks for reading,\n[Your name]"),
]
SEND_CHECK = [
    "Subject line checked and preview text written", "Sent a test to yourself and read it on your phone", "Every link works and goes where you say",
    "Unsubscribe link is in the footer (UK rules for marketing email require an easy opt-out)",
    "Your name and a way to contact you (or your business address) is in the footer",
    "Affiliate links or sponsors are clearly disclosed", "Images have alt text and the email still reads without them",
    "You have proofread it once out loud", "You are only emailing people who agreed to hear from you",
]


def _data(settings: Settings) -> dict:
    d = wi.load(settings, wi.NEWSLETTER, {})
    for key in ("issues", "subs", "opens", "welcome"):
        if not isinstance(d.get(key), list):
            d[key] = []
    return d


def _label(row: dict) -> str:
    return f"#{row['id']} {row['title']}"


def plan_issue(settings: Settings, args: dict):
    d = _data(settings)
    if len(d["issues"]) >= wi.MAX_ROWS:
        raise ValueError("The issue calendar is full; remove old issues first.")
    status = wi.clean(args.get("status")).lower() or "idea"
    if status not in STATUSES:
        raise ValueError("Status should be idea, drafting, ready or sent.")
    row = {"id": wi.next_id(d["issues"]), "title": wi.need(args.get("title"), "issue title", 100), "status": status,
           "date": (wi.parse_date(args.get("date"), "send date") or wi.today()).isoformat(),
           "subject": wi.clean(args.get("subject"), 120), "notes": wi.clean(args.get("notes"), 300)}
    d["issues"].append(row)
    wi.save(settings, wi.NEWSLETTER, d)
    return f"Planned issue {row['id']}, {row['title']}, for {wi.short(wi.parse_date(row['date']))} as {status}."


def issue_calendar(settings: Settings, args: dict):
    d = _data(settings)
    rows = sorted(d["issues"], key=lambda r: r["date"])
    if not args.get("all"):
        rows = [r for r in rows if r["status"] != "sent"]
    if not rows:
        raise ValueError("No issues planned. Say a title and a send date to plan one.")
    now = wi.today()
    table = [[str(r["id"]), wi.short(wi.parse_date(r["date"])) + " (" + wi.until(wi.parse_date(r["date"]), now) + ")", r["title"],
              r["status"], r["subject"]] for r in rows[:40]]
    later = [r for r in rows if wi.parse_date(r["date"]) >= now]
    gap = "" if later and wi.parse_date(later[0]["date"]) <= now + timedelta(days=14) else " Nothing is planned in the next two weeks."
    return wi.table(f"{len(rows)} issues on the calendar.{gap}", "Newsletter calendar", ["#", "Send", "Issue", "Status", "Subject"], table)


def update_issue(settings: Settings, args: dict):
    d = _data(settings)
    row = wi.pick(d["issues"], args.get("issue"), "title", "issue")
    if args.get("status"):
        status = wi.clean(args["status"]).lower()
        if status not in STATUSES:
            raise ValueError("Status should be idea, drafting, ready or sent.")
        row["status"] = status
    if args.get("date"):
        row["date"] = wi.parse_date(args["date"], "send date").isoformat()
    for key, limit in (("subject", 120), ("notes", 300)):
        if args.get(key) is not None:
            row[key] = wi.clean(args[key], limit)
    if args.get("title"):
        row["title"] = wi.clean(args["title"], 100)
    wi.save(settings, wi.NEWSLETTER, d)
    return f"Updated {_label(row)}: {row['status']}, {wi.short(wi.parse_date(row['date']))}."


def remove_issue(settings: Settings, args: dict):
    d = _data(settings)
    row = wi.pick(d["issues"], args.get("issue"), "title", "issue")
    ask = wi.confirm_first(args, f"issue {_label(row)} from the calendar")
    if ask:
        return ask
    d["issues"] = [r for r in d["issues"] if r is not row]
    wi.save(settings, wi.NEWSLETTER, d)
    return f"Removed {_label(row)}."


def sections_template(settings: Settings, args: dict):
    key = wi.clean(args.get("kind")).lower()
    hits = [k for k in TEMPLATES if key and key in k]
    if key and not hits:
        raise ValueError("Pick a template: " + ", ".join(TEMPLATES) + ".")
    keys = hits or list(TEMPLATES)
    return wi.guide("Newsletter issue layouts you can copy.", "Issue sections", [(TEMPLATES[k][0], TEMPLATES[k][1]) for k in keys],
                    "Keep one main idea per issue. Short, regular issues beat long, rare ones.")


def subject_lines(settings: Settings, args: dict):
    topic = wi.need(args.get("topic"), "topic", 60).lower()
    number = wi.whole(args, "count", "number", default=5, top=9)
    options = [
        ("Curiosity", f"The {topic} mistake I keep seeing"), ("Number", f"{number} small {topic} changes worth making"),
        ("Question", f"Are you getting {topic} wrong?"), ("Benefit", f"Get better at {topic} this week"),
        ("How-to", f"How I approach {topic}, step by step"), ("Short", f"About {topic}"),
        ("Personal", f"What I learned about {topic} this month"), ("Story", f"I tried {topic} for 30 days"),
        ("Direct", f"Your {topic} checklist"), ("Contrarian", f"Why most {topic} advice misses the point"),
        ("Update", f"This week in {topic}"), ("Reply bait", f"Quick question about {topic}"),
    ]
    items = [{"label": f"{style}: {line}", "say": f"Check this subject line: {line}"} for style, line in options]
    return screen.Shown(f"Twelve subject line starters for {topic}. Tap one to check it.", screen.card(
        "list", f"Subject lines: {topic}", "writingincome-subjects", items=items,
        text="Starters to reword in your own voice. Be honest: the email must deliver what the subject promises."))


def check_subject(settings: Settings, args: dict):
    line = wi.need(args.get("subject"), "subject line", 200)
    words = wi.words_of(line)
    lower = line.lower()
    found = [w for w in SPAM if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", lower)]
    caps = [w for w in words if len(w) > 2 and w.isupper()]
    emoji = len(re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", line))
    n = len(line)
    items = [("Length", "ok" if 20 <= n <= 50 else "warn", f"{n} characters. Around 30 to 50 usually shows fully on a phone."),
             ("Words", "ok" if 3 <= len(words) <= 9 else "warn", f"{len(words)} words. Roughly 4 to 9 works well."),
             ("Spammy words", "fail" if found else "ok", ("Watch: " + ", ".join(found)) if found else "None of the usual trigger words."),
             ("Shouting", "warn" if caps or "!!" in line else "ok",
              "ALL CAPS or repeated exclamation marks look like spam." if caps or "!!" in line else "No shouting."),
             ("Emoji", "warn" if emoji > 1 else "ok", f"{emoji} emoji. One at most is plenty."),
             ("Honest", "warn" if re.match(r"(re|fwd?):", lower) else "ok",
              "Starting with Re: or Fwd: pretends it's a reply; don't." if re.match(r"(re|fwd?):", lower) else "No fake reply prefix.")]
    preview = wi.clean(args.get("preview"), 300)
    if preview:
        items.append(("Preview text", "ok" if 40 <= len(preview) <= 110 else "warn", f"{len(preview)} characters. About 40 to 110 is a good range."))
    bad = sum(1 for i in items if i[1] == "fail") + sum(1 for i in items if i[1] == "warn")
    head = "Looks good" if bad == 0 else f"{bad} thing{'s' if bad != 1 else ''} to look at"
    return wi.check(f"{head} for that subject line.", "Subject line check", head, items,
                    "Rules of thumb, not guarantees. Test your own audience and keep the subject truthful.")


def log_subscribers(settings: Settings, args: dict):
    d = _data(settings)
    count = wi.whole(args, "count", "subscriber count", zero=True)
    day = wi.day_arg(args).isoformat()
    d["subs"] = [r for r in d["subs"] if r["date"] != day] + [{"date": day, "count": count, "note": wi.clean(args.get("notes"), 120)}]
    d["subs"].sort(key=lambda r: r["date"])
    wi.save(settings, wi.NEWSLETTER, d)
    before = [r for r in d["subs"] if r["date"] < day]
    change = f" That's {count - before[-1]['count']:+d} since {wi.short(wi.parse_date(before[-1]['date']))}." if before else ""
    return f"Logged {count} subscribers for {wi.short(wi.parse_date(day))}.{change}"


def subscriber_growth(settings: Settings, args: dict):
    rows = _data(settings)["subs"]
    if len(rows) < 2:
        raise ValueError("Log the subscriber count on at least two different days to see growth.")
    first, last = rows[0], rows[-1]
    days = max((wi.parse_date(last["date"]) - wi.parse_date(first["date"])).days, 1)
    gained = last["count"] - first["count"]
    per_week = round(gained * 7 / days, 1)
    text = f"{last['count']} subscribers, {gained:+d} over {days} days, about {per_week:+g} a week."
    if args.get("target"):
        goal = wi.whole(args, "target", "target")
        if per_week > 0 and goal > last["count"]:
            weeks = -(-(goal - last["count"]) // per_week)
            text += f" At exactly that pace you'd reach {goal} in about {int(weeks)} weeks, but growth is never steady, so treat it as a rough guess."
        elif goal > last["count"]:
            text += " At the current pace you wouldn't reach that target."
    return wi.chart(text, "Subscribers", [wi.short(wi.parse_date(r["date"])) for r in rows[-30:]], [r["count"] for r in rows[-30:]],
                    "line", "subs", "writingincome-subs")


def log_opens(settings: Settings, args: dict):
    d = _data(settings)
    sent, opened = wi.whole(args, "sent", "number sent"), wi.whole(args, "opened", "number of opens", zero=True)
    if opened > sent:
        raise ValueError("Opens can't be more than the number sent (unique opens).")
    clicked = wi.whole(args, "clicked", "number of clicks", zero=True, default=0)
    row = {"id": wi.next_id(d["opens"]), "issue": wi.need(args.get("issue"), "issue name", 100), "date": wi.day_arg(args).isoformat(),
           "sent": sent, "opened": opened, "clicked": clicked}
    d["opens"].append(row)
    wi.save(settings, wi.NEWSLETTER, d)
    return (f"Logged {row['issue']}: {round(100 * opened / sent, 1)}% opened"
            + (f", {round(100 * clicked / sent, 1)}% clicked." if clicked else "."))


def open_rate_report(settings: Settings, args: dict):
    rows = _data(settings)["opens"]
    if not rows:
        raise ValueError("No open rates logged yet. Say the issue, how many were sent and how many opened.")
    rates = [round(100 * r["opened"] / r["sent"], 1) for r in rows]
    avg = round(sum(rates) / len(rates), 1)
    best = rows[rates.index(max(rates))]
    text = (f"Average open rate {avg}% over {len(rows)} issues. Best was {best['issue']} at {max(rates)}%. "
            "Opens can be inflated by privacy features, so clicks and replies say more.")
    return wi.chart(text, "Open rate by issue", [r["issue"][:14] for r in rows[-20:]], rates[-20:], "bar", "%", "writingincome-opens")


def welcome_sequence(settings: Settings, args: dict):
    d = _data(settings)
    count = wi.whole(args, "count", "number of emails", default=4, top=len(WELCOME))
    gift = wi.clean(args.get("topic"), 60) or "free guide"
    saved = {w["n"]: w for w in d["welcome"]}
    rows = []
    for n, (day, subject, purpose, body) in enumerate(WELCOME[:max(count, 1)], 1):
        mine = saved.get(n, {})
        rows.append((f"Email {n}, day {day}: {mine.get('subject') or subject.format(gift=gift)}",
                     [purpose] + (mine.get("body") or body).split("\n\n")))
    return wi.guide(f"A {count} email welcome sequence. These are drafts for you to edit and send yourself.", "Welcome emails", rows,
                    "Nothing is sent. Ask me to save your edited version of an email. Keep it friendly and tell them how to unsubscribe.")


def welcome_edit(settings: Settings, args: dict):
    d = _data(settings)
    n = wi.whole(args, "email_number", "email number", top=len(WELCOME))
    body = str(args.get("body") or "").strip()[:4000]
    if not body:
        raise ValueError("Give me the email text to save.")
    d["welcome"] = [w for w in d["welcome"] if w["n"] != n] + [{"n": n, "subject": wi.clean(args.get("subject"), 120), "body": body}]
    wi.save(settings, wi.NEWSLETTER, d)
    return f"Saved your version of welcome email {n}."


def lead_magnet_ideas(settings: Settings, args: dict):
    topic = wi.clean(args.get("topic"), 60) or "your topic"
    rows = [[name, f"{what} about {topic}", effort] for name, what, effort in LEAD_MAGNETS]
    return wi.table("Twelve lead magnet ideas. Pick one that takes you an evening, not a month.", "Lead magnet ideas",
                    ["Idea", "What it could be", "Effort"], rows, "writingincome-magnets")


def send_checklist(settings: Settings, args: dict):
    items = [{"label": s, "done": False, "say": ""} for s in SEND_CHECK]
    return screen.Shown("Before-you-send checklist for a newsletter issue.", screen.card(
        "list", "Before you send", "writingincome-sendcheck", items=items, checks=True,
        text="General good practice, not legal advice. Check GOV.UK and the ICO for email marketing rules."))


ACTIONS = {"plan_issue": plan_issue, "issue_calendar": issue_calendar, "update_issue": update_issue, "remove_issue": remove_issue,
           "sections_template": sections_template, "subject_lines": subject_lines, "check_subject": check_subject,
           "log_subscribers": log_subscribers, "subscriber_growth": subscriber_growth, "log_opens": log_opens,
           "open_rate_report": open_rate_report, "welcome_sequence": welcome_sequence, "welcome_edit": welcome_edit,
           "lead_magnet_ideas": lead_magnet_ideas, "send_checklist": send_checklist}


def tool_definitions() -> list[dict]:
    return [{
        "name": "writingincome_newsletter",
        "description": "Newsletter planner for writers: issue calendar (plan, list, update, remove), issue section templates, subject line "
                       "ideas and checker, log subscriber counts (typed by the user) with growth chart, open rate log and chart, welcome "
                       "email sequence drafts, lead magnet ideas, before-you-send checklist. Nothing is sent. Set confirmed only after "
                       "the user agrees to remove_issue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "title": {"type": "string"}, "issue": {"type": "string", "description": "Issue number or name."},
                "status": {"type": "string", "enum": STATUSES}, "date": {"type": "string", "description": "YYYY-MM-DD."},
                "subject": {"type": "string"}, "preview": {"type": "string", "description": "Preview text to check."},
                "notes": {"type": "string"}, "topic": {"type": "string"}, "kind": {"type": "string", "description": "digest, essay, tips or personal."},
                "count": {"type": "number", "description": "subject_lines: how many; log_subscribers: subscriber count; welcome_sequence: emails."},
                "target": {"type": "number", "description": "subscriber_growth: a subscriber goal."},
                "sent": {"type": "number"}, "opened": {"type": "number"}, "clicked": {"type": "number"},
                "email_number": {"type": "number"}, "body": {"type": "string"}, "all": {"type": "boolean"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    return wi.dispatch(ACTIONS, settings, args)
