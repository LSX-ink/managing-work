"""Paid-writing money helpers: paid subscription maths (subscribers x price minus platform and card fees), subscribers
needed for a goal, free-to-paid what-ifs, break-even, per-word and hourly rates, affiliate disclosure wording, and a
pitch-to-publication tracker for paid articles (drafts and notes only, nothing is ever sent).

Data is in writingincome-pitches.json in the memory folder. Fee presets are approximate and change: every sum says to check
the platform's own page. Nothing here promises income; UK tax notes are general guidance and point to GOV.UK.
"""

import writingincome_store as wi
from config import Settings

NAMES = {"writingincome_money"}
PLATFORMS = {"substack": (10.0, "Substack takes about 10% plus card fees."), "ghost": (0.0, "Ghost charges a monthly plan instead of a cut (add it as monthly_costs)."),
             "custom": (0.0, "Your own figures."), "none": (0.0, "No platform cut.")}
STATUSES = ["idea", "drafted", "pitched", "accepted", "published", "paid", "rejected"]
FOLLOW_UP_DAYS = 14


def _fees(args: dict) -> dict:
    name = wi.clean(args.get("platform")).lower() or "custom"
    if name.startswith("medium"):
        raise ValueError("Medium pays from how much members read, so there's no subscribers-times-price sum. Type your own monthly estimate instead.")
    if name not in PLATFORMS:
        raise ValueError("Platform: substack, ghost, none or custom (then give platform_pct).")
    pct = wi.arg(args, "platform_pct", "platform percentage", zero=True, default=PLATFORMS[name][0], top=60)
    return {"name": name, "pct": pct, "card_pct": wi.arg(args, "card_pct", "card fee percentage", zero=True, default=2.9, top=20),
            "card_fixed": wi.arg(args, "card_fixed", "fixed card fee per payment", zero=True, default=0.30), "note": PLATFORMS[name][1]}


def _net(args: dict, fees: dict) -> dict:
    """Take-home per subscriber per month, and the fees taken, for a monthly or yearly plan."""
    price = wi.arg(args, "price", "subscription price")
    yearly = wi.clean(args.get("billing")).lower().startswith(("y", "a"))
    cut = price * (fees["pct"] + fees["card_pct"]) / 100 + fees["card_fixed"]
    per = 12 if yearly else 1
    return {"price": price, "yearly": yearly, "gross_month": price / per, "fees_month": cut / per, "net_month": (price - cut) / per}


def paid_subs_calc(settings: Settings, args: dict):
    fees, subs = _fees(args), wi.whole(args, "subscribers", "number of paid subscribers")
    net = _net(args, fees)
    costs = wi.arg(args, "monthly_costs", "monthly costs", zero=True, default=0.0)
    gross, taken = subs * net["gross_month"], subs * net["fees_month"]
    home = round(gross - taken - costs, 2)
    rows = [(f"{subs:,} subscribers x {wi.pounds(net['price'])} {'a year' if net['yearly'] else 'a month'}", wi.pounds(round(gross, 2)) + " a month"),
            (f"Platform {fees['pct']:g}% + card {fees['card_pct']:g}% + {wi.pounds(fees['card_fixed'])} a payment", "-" + wi.pounds(round(taken, 2))),
            ("Your monthly costs", "-" + wi.pounds(costs)), ("Per year", wi.pounds(round(home * 12, 2)))]
    return wi.result(f"About {wi.pounds(home)} a month before tax from {subs:,} paid subscribers. {wi.HONEST}", "Paid subscription maths", wi.pounds(home),
                     "a month before tax, if the numbers hold", rows,
                     [fees["note"] + " Fees change and depend on card type and country: check the platform's own page.", wi.TAX, wi.HONEST])


def paid_goal(settings: Settings, args: dict):
    fees = _fees(args)
    net = _net(args, fees)
    goal, costs = wi.arg(args, "target", "monthly amount you want"), wi.arg(args, "monthly_costs", "monthly costs", zero=True, default=0.0)
    if net["net_month"] <= 0:
        raise ValueError("At that price the fees take everything, so a higher price is needed.")
    need = -(-(goal + costs) // net["net_month"])
    return wi.result(f"You'd need about {int(need):,} paid subscribers to take home {wi.pounds(goal)} a month. That's a what-if, not a forecast.",
                     "Subscribers needed", f"{int(need):,}", "paid subscribers",
                     [("Take-home per subscriber a month", wi.pounds(round(net["net_month"], 2))), ("Goal plus costs", wi.pounds(goal + costs))],
                     [fees["note"], wi.HONEST])


def conversion_whatif(settings: Settings, args: dict):
    fees, free = _fees(args), wi.whole(args, "subscribers", "number of free subscribers")
    net = _net(args, fees)
    costs = wi.arg(args, "monthly_costs", "monthly costs", zero=True, default=0.0)
    rows = []
    for pct in (1, 2, 3, 5, 10):
        paid = round(free * pct / 100)
        rows.append([f"{pct}%", f"{paid:,}", wi.pounds(round(paid * net["net_month"] - costs, 2))])
    return wi.table(f"What-if: {free:,} free subscribers turning paid at different rates. Real conversion varies a lot and can be lower.",
                    "Free to paid what-if", ["Convert", "Paid subscribers", "Monthly take-home"], rows, "writingincome-conversion")


def break_even(settings: Settings, args: dict):
    fees = _fees(args)
    net = _net(args, fees)
    costs = wi.arg(args, "monthly_costs", "monthly costs of running it")
    if net["net_month"] <= 0:
        raise ValueError("At that price the fees take everything, so a higher price is needed.")
    n = -(-costs // net["net_month"])
    return wi.result(f"You'd need about {int(n):,} paid subscribers to cover {wi.pounds(costs)} a month of costs.", "Break-even", f"{int(n):,}",
                     "paid subscribers to cover costs", [("Costs a month", wi.pounds(costs)), ("Take-home per subscriber", wi.pounds(round(net["net_month"], 2)))],
                     [wi.HONEST])


def per_word_rate(settings: Settings, args: dict):
    fee, words = wi.arg(args, "fee", "fee for the piece"), wi.whole(args, "words", "word count")
    hours = wi.arg(args, "hours", "hours spent", default=0.0)
    rows = [("Fee", wi.pounds(fee)), ("Words", f"{words:,}"), ("Per word", f"{round(100 * fee / words, 1):g}p")]
    head = f"{round(100 * fee / words, 1):g}p a word"
    if hours:
        hourly = round(fee / hours, 2)
        rows += [("Hours", f"{hours:g}"), ("Per hour", wi.pounds(hourly))]
        head += f", {wi.pounds(hourly)} an hour"
    return wi.result(f"That works out at {head}.", "Rate check", head, "before tax and expenses", rows,
                     ["Count research, pitching and edits in your hours to see the true hourly rate.", wi.TAX])


def affiliate_disclosure(settings: Settings, args: dict):
    where = wi.clean(args.get("where")).lower() or "blog"
    amazon = bool(args.get("amazon"))
    short = {"blog": "This post contains affiliate links. If you buy through them I may earn a small commission at no extra cost to you.",
             "newsletter": "Some links in this email are affiliate links. If you buy through them I may earn a small commission, at no extra cost to you.",
             "social": "#ad Affiliate link: I may earn a commission if you buy.", "video": "Some links in the description are affiliate links, so I may earn a commission.",
             "book": "Some links in this book are affiliate links; I may earn a commission if you buy through them."}
    if where not in short:
        raise ValueError("Where will it go? blog, newsletter, social, video or book.")
    lines = [short[where]]
    if amazon:
        lines.append("As an Amazon Associate I earn from qualifying purchases. (Amazon's programme requires this wording, so check the current terms.)")
    return wi.guide(f"Draft affiliate disclosure for a {where}.", "Affiliate disclosure", [
        ("Text you can use", lines),
        ("Where to put it", ["Near the top, before the first affiliate link, in plain words, not hidden in a footer or small print.",
                             "Say 'ad' or 'affiliate' clearly. 'Sponsored' or 'gifted' are different, so say which applies."]),
        ("Why", ["UK rules from the ASA and CMA say paid or affiliate content must be obvious."])],
        "General guidance, not legal advice. Check the ASA, CMA and GOV.UK guidance and each programme's own terms.")


def _data(settings: Settings) -> dict:
    d = wi.load(settings, wi.PITCHES, {})
    if not isinstance(d.get("pitches"), list):
        d["pitches"] = []
    return d


def _pitch(d: dict, ref) -> dict:
    return wi.pick(d["pitches"], ref, "idea", "pitch")


def _status(value, default: str = "idea") -> str:
    status = wi.clean(value).lower() or default
    if status not in STATUSES:
        raise ValueError("Status should be one of: " + ", ".join(STATUSES) + ".")
    return status


def pitch_add(settings: Settings, args: dict):
    d = _data(settings)
    if len(d["pitches"]) >= wi.MAX_ROWS:
        raise ValueError("The pitch list is full; remove old ones first.")
    status = _status(args.get("status"))
    row = {"id": wi.next_id(d["pitches"]), "publication": wi.need(args.get("publication"), "publication", 80),
           "idea": wi.need(args.get("idea"), "article idea", 120), "status": status, "fee": wi.arg(args, "fee", "fee", zero=True, default=0.0),
           "date": wi.day_arg(args).isoformat(), "notes": wi.clean(args.get("notes"), 300)}
    d["pitches"].append(row)
    wi.save(settings, wi.PITCHES, d)
    return f"Tracking pitch {row['id']}: {row['idea']} for {row['publication']} ({status}). Nothing has been sent."


def pitch_update(settings: Settings, args: dict):
    d = _data(settings)
    row = _pitch(d, args.get("pitch"))
    if args.get("status"):
        row["status"] = _status(args["status"])
        row["date"] = wi.day_arg(args).isoformat()
    if args.get("fee") is not None:
        row["fee"] = wi.arg(args, "fee", "fee", zero=True)
    if args.get("notes") is not None:
        row["notes"] = wi.clean(args["notes"], 300)
    wi.save(settings, wi.PITCHES, d)
    return f"Pitch {row['id']}, {row['idea']}, is now {row['status']}."


def pitch_remove(settings: Settings, args: dict):
    d = _data(settings)
    row = _pitch(d, args.get("pitch"))
    ask = wi.confirm_first(args, f"the pitch {row['idea']} from the tracker")
    if ask:
        return ask
    d["pitches"] = [p for p in d["pitches"] if p is not row]
    wi.save(settings, wi.PITCHES, d)
    return f"Removed {row['idea']}."


def pitch_board(settings: Settings, args: dict):
    d = _data(settings)
    if not d["pitches"]:
        raise ValueError("No pitches yet. Say the publication and your article idea.")
    now = wi.today()
    cols, nudges = [], []
    for status in STATUSES:
        cards = []
        for p in [p for p in d["pitches"] if p["status"] == status]:
            small = p["publication"] + (f" · {wi.pounds(p['fee'])}" if p["fee"] else "")
            if status == "pitched" and (now - wi.parse_date(p["date"])).days >= FOLLOW_UP_DAYS:
                nudges.append(p["idea"])
                small += " · follow up?"
            cards.append((p["idea"], small, f"Change the status of pitch {p['id']}, {p['idea']}"))
        if cards:
            cols.append((f"{status.title()} ({len(cards)})", cards))
    owed = sum(p["fee"] for p in d["pitches"] if p["status"] in ("accepted", "published"))
    note = f"Agreed but not yet paid: {wi.pounds(owed)}. " if owed else ""
    note += ("It has been over two weeks since you pitched: " + ", ".join(nudges[:3]) + ". A polite follow-up is fine if their guidelines allow it. ") if nudges else ""
    return wi.board(f"{len(d['pitches'])} pitches tracked. Nothing is ever sent from here.", "Pitch tracker", cols, note.strip())


def pitch_template(settings: Settings, args: dict):
    return wi.guide("A pitch structure. I draft the words; you send it yourself.", "Pitch draft", [
        ("Subject line", ["Pitch: [your specific angle in under ten words]"]),
        ("Opening", ["Hi [editor's name], one sentence on the story and why it suits [publication]'s readers."]),
        ("The idea", ["Two or three sentences: the angle, what is new, and what readers will take away."]),
        ("Why you", ["One or two lines on your experience, with two or three links to your best published work."]),
        ("Practical", ["Suggested length, when you could deliver it, and whether you'd like to be paid a set fee (check their guidelines)."]),
        ("Close", ["Thanks, [your name]. Keep it under 200 words."])],
        "Read the publication's submission guidelines first and follow them exactly. Never send the same pitch to publications that forbid simultaneous pitches.")


def honest_guide(settings: Settings, args: dict):
    return wi.guide("Some honest notes on earning from writing.", "Writing income, honestly", [
        ("Expect a slow start", ["Most newsletters, blogs and books earn very little for a long time. Nothing in Alfred predicts your income."]),
        ("Keep your costs low", ["Start with free or cheap tools and track what you spend."]),
        ("Be open with readers", ["Disclose affiliate links, sponsors and gifted items clearly."]),
        ("Never buy reviews or followers", ["It breaks platform rules and can get you banned."]),
        ("Tax", ["Writing income, including royalties, affiliate income and article fees, may need declaring. Keep records of money in and out.", wi.TAX])],
        "Alfred works from your own numbers and never guarantees earnings.")


ACTIONS = {"paid_subs_calc": paid_subs_calc, "paid_goal": paid_goal, "conversion_whatif": conversion_whatif, "break_even": break_even,
           "per_word_rate": per_word_rate, "affiliate_disclosure": affiliate_disclosure, "pitch_add": pitch_add, "pitch_update": pitch_update,
           "pitch_board": pitch_board, "pitch_template": pitch_template, "pitch_remove": pitch_remove, "honest_guide": honest_guide}


def tool_definitions() -> list[dict]:
    return [{
        "name": "writingincome_money",
        "description": "Money helpers for writers: paid subscription maths (Substack-style: subscribers x price minus platform % and card fees), "
                       "subscribers needed for a goal, free-to-paid what-ifs, break-even, per-word and hourly rate, affiliate disclosure wording "
                       "(UK), pitch-to-publication tracker for paid articles and pitch structure (drafts only, never sent), honest income notes. "
                       "Never promises income. Set confirmed only after the user agrees to pitch_remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "subscribers": {"type": "number", "description": "Paid subscribers (free subscribers for conversion_whatif)."},
                "price": {"type": "number"}, "billing": {"type": "string", "enum": ["monthly", "yearly"]},
                "platform": {"type": "string", "description": "substack, ghost, none or custom."}, "platform_pct": {"type": "number"},
                "card_pct": {"type": "number"}, "card_fixed": {"type": "number"}, "monthly_costs": {"type": "number"},
                "target": {"type": "number", "description": "Monthly take-home wanted."}, "fee": {"type": "number"}, "words": {"type": "number"},
                "hours": {"type": "number"}, "where": {"type": "string", "description": "blog, newsletter, social, video or book."},
                "amazon": {"type": "boolean", "description": "Add the Amazon Associates line."},
                "publication": {"type": "string"}, "idea": {"type": "string"}, "pitch": {"type": "string", "description": "Pitch number or idea."},
                "status": {"type": "string", "enum": STATUSES}, "date": {"type": "string", "description": "YYYY-MM-DD."}, "notes": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    return wi.dispatch(ACTIONS, settings, args)
