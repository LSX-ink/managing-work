"""Creator paperwork and plain-words guides: media kit (Markdown or HTML file), email drafts to brands (drafts only, never
sent), a contract checklist you can tick per deal, and short UK guides on #ad disclosure, usage rights, exclusivity,
payment terms and tax.

The checklist pops up as "creatorbiz-checklist" (frontend/popup-creatorbiz.js). The guides are general information, not
legal or tax advice: they always point to current ASA/CMA guidance and GOV.UK.
"""

import html

import creatorbiz_store as cb
import screen
from config import Settings

KIND = "creatorbiz-checklist"
screen.EXTRA_KINDS.add(KIND)
NAMES = {"creator_docs"}
KIT_FIELDS = ["name", "niche", "bio", "audience", "platforms", "avg_views", "past_work", "services", "contact", "pay_to"]
ACTIONS = ["kit_set", "kit_show", "kit_build", "pitch_draft", "followup_draft", "negotiation_draft", "decline_draft",
           "contract_checklist", "contract_tick", "disclosure_guide", "usage_rights", "exclusivity", "payment_terms",
           "brand_questions", "red_flags", "tax_guide", "negotiation_tips"]
LEGAL = "General information only, not legal advice. For a big or unusual contract, ask a solicitor."
CHECKLIST = [
    ("scope", "What exactly you must make", "The number and type of posts, the platforms, and the dates, all written down."),
    ("fee", "The fee in pounds", "The total, whether VAT is included, and what happens to any free product."),
    ("payment", "Payment terms", "How many days after your invoice they pay. Shorter is better for you; 30 days is common."),
    ("usage", "Usage rights", "Whether the brand can reuse your video or photos, where (their own page, paid ads) and for how long."),
    ("exclusivity", "Exclusivity", "Whether you must avoid rival brands, which ones, and for how long."),
    ("disclosure", "#ad and disclosure", "Agreement that the content will be clearly labelled as an ad, as UK rules expect."),
    ("approval", "Approval and edits", "Who approves the draft, how many rounds of changes, and how fast they must reply."),
    ("deadlines", "Deadlines", "The date drafts and final posts are due, and what happens if a date slips."),
    ("cancellation", "Cancelling", "What you're paid if they cancel after you've started, and what if you can't deliver."),
    ("ownership", "Who owns the content", "You normally keep ownership and give the brand a licence; check it isn't a full hand-over."),
    ("ads_access", "Paid ads on your account", "If they want to run ads through your handle, agree the length and cost."),
    ("claims", "What you can say", "Any claims about the product must be true and provable; ask for their approved wording."),
]
GUIDES = {
    "disclosure_guide": ("Advertising and #ad in the UK", [
        "If a brand pays you, gives you a reward, or you have any deal that shapes what you post, it is an advert and must be obvious.",
        "Say it clearly and early: 'Ad' or '#ad' at the start of the caption, and say it in the video or on screen too.",
        "Vague labels such as 'sp', 'collab', 'thanks to', or hiding #ad in a pile of hashtags are not clear enough.",
        "Gifted items you were free to review honestly can still need a label if the brand expects a mention. Affiliate links count.",
        "Use the app's paid partnership label as well, but don't rely on it alone.",
        "The rules come from the ASA and the CMA. Check their current guidance on asa.org.uk and gov.uk before you post."]),
    "usage_rights": ("Usage rights in plain words", [
        "Usage rights say what the brand may do with your content after you post it.",
        "Organic reposting on their own page is small. Using it in paid ads, on their website, or in shops is worth more.",
        "Always agree where, for how long, and whether there's an extra fee. 'Forever' is a red flag.",
        "Rate estimates often add a percentage on top for paid usage. Alfred's rate card does this too, as a rough guide.",
        LEGAL]),
    "exclusivity": ("Exclusivity in plain words", [
        "Exclusivity means you agree not to work with rival brands for a period.",
        "Check exactly which brands or categories count, how long it lasts, and whether it starts at signing or at posting.",
        "It limits other income, so it should be priced. Keep it narrow and short if you can.",
        LEGAL]),
    "payment_terms": ("Payment terms in plain words", [
        "Payment terms are how long the brand takes to pay after you invoice, such as 14, 30 or 60 days.",
        "Ask for the terms in writing, send the invoice as soon as the work is delivered, and note the due date.",
        "For bigger fees, ask for part up front, for example half at signing.",
        "If a business pays late, UK law lets you claim interest and costs on some business invoices. Check GOV.UK for the current rules.",
        LEGAL]),
    "brand_questions": ("Questions to ask a brand before agreeing", [
        "What is the campaign for and who is it aimed at?", "Exactly how many pieces, on which platforms, by when?",
        "Is the fee for one piece or all of them, and is VAT involved?", "Will you reuse the content anywhere, and for how long?",
        "Do you want exclusivity, and with whom?", "Who approves drafts, and how many changes are included?",
        "When will you pay, and can part be paid up front?", "Is there a written contract I can read before starting?"]),
    "red_flags": ("Red flags to watch for", [
        "They ask you to pay first, pay for the product, or buy a 'starter kit' to join.",
        "They pressure you to sign or post today and won't put terms in writing.",
        "Usage rights that last forever or cover everything, with no extra fee.",
        "They tell you not to label posts as ads. That puts you at risk.",
        "Payment only in 'exposure', or 'commission' with unclear terms.",
        "A real-looking email from a free address or a slightly wrong brand name. Check it is who it says it is.",
        "Never share passwords or log-ins. Brands never need them."]),
    "tax_guide": ("UK tax basics for creators (general, not advice)", [
        "Money from brands, affiliates and platforms is usually income, even if it's small.",
        "There is a trading allowance for small side income; the amount and the rules change, so check GOV.UK.",
        "If you go over it you generally need to register for Self Assessment; check the deadlines on GOV.UK.",
        "You can usually deduct genuine business costs such as equipment or software; keep receipts.",
        "Free gifts given as part of a deal can count as income too.",
        "Alfred's totals are a tidy summary of numbers you typed in. They are not tax advice; ask an accountant or check GOV.UK."]),
    "negotiation_tips": ("Negotiating a brand deal", [
        "Know your lowest acceptable fee before the call, and quote a range or a figure a little above it.",
        "Price usage rights, exclusivity and rush jobs separately instead of giving them away.",
        "If the budget is small, offer fewer deliverables rather than the same work for less.",
        "Ask for a deposit and shorter payment terms, and get everything confirmed in writing.",
        "You can always say no. Brands come back to creators who are clear and professional.",
        "Alfred's rate card is only a rough estimate, and no deal or income is ever guaranteed."]),
}


def _profile(settings: Settings) -> dict:
    return cb.load(settings, cb.PROFILE, {})


def kit_set(settings: Settings, args: dict) -> str:
    prof = _profile(settings)
    changed = []
    for key in KIT_FIELDS:
        if args.get(key) not in (None, ""):
            prof[key] = int(args[key]) if key == "avg_views" else cb.clean(args[key], 600)
            changed.append(key.replace("_", " "))
    if not changed:
        raise ValueError("What should I save? For example your name, niche, bio, audience or platforms.")
    cb.save(settings, cb.PROFILE, prof)
    return f"Saved your {', '.join(changed)} for your media kit."


def _kit_lines(prof: dict) -> list[tuple[str, str]]:
    labels = [("niche", "Niche"), ("bio", "About"), ("audience", "Audience"), ("platforms", "Platforms and followers"),
              ("avg_views", "Typical views per video"), ("past_work", "Past work"), ("services", "What I offer"),
              ("contact", "Contact")]
    return [(label, f"{prof[key]:,}" if key == "avg_views" else str(prof[key])) for key, label in labels if prof.get(key)]


def kit_show(settings: Settings) -> screen.Shown:
    prof = _profile(settings)
    lines = _kit_lines(prof)
    if not lines:
        raise ValueError("Your media kit is empty. Tell me your niche, bio, audience and platforms first.")
    text = "\n".join(f"{k}: {v}" for k, v in lines)
    missing = [k for k in ("bio", "audience", "platforms", "contact") if not prof.get(k)]
    tip = f" Still missing: {', '.join(missing)}." if missing else ""
    return screen.Shown(f"Here's your media kit profile.{tip}", screen.card(
        "text", prof.get("name") or "Media kit", "creatorbiz-kit", text=text,
        buttons=[{"label": "Build the file", "say": "Build my media kit as a file."}]))


def _kit_md(prof: dict) -> str:
    out = [f"# {prof.get('name') or 'Creator'} - media kit", ""]
    for label, value in _kit_lines(prof):
        out += [f"## {label}", value, ""]
    out += ["## Rates", "Available on request; each campaign is quoted individually.", "",
            f"_Updated {cb.long_date(cb.today())}. Paid partnerships are always labelled as ads._"]
    return "\n".join(out) + "\n"


def _kit_html(prof: dict) -> str:
    esc = html.escape
    body = "".join(f"<h2>{esc(label)}</h2><p>{esc(value)}</p>" for label, value in _kit_lines(prof))
    return ("<!doctype html><html lang='en-GB'><head><meta charset='utf-8'><title>Media kit</title><style>"
            "body{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem;background:#000;color:#fff}"
            "h1{letter-spacing:.05em}h2{font-size:.85rem;letter-spacing:.15em;text-transform:uppercase;color:#aaa}</style></head><body>"
            f"<h1>{esc(prof.get('name') or 'Creator')} - media kit</h1>{body}<h2>Rates</h2><p>Available on request.</p>"
            f"<p><small>Updated {esc(cb.long_date(cb.today()))}. Paid partnerships are always labelled as ads.</small></p></body></html>\n")


def kit_build(settings: Settings, args: dict) -> screen.Shown:
    prof = _profile(settings)
    if not _kit_lines(prof):
        raise ValueError("Your media kit is empty. Tell me your niche, bio, audience and platforms first.")
    fmt = cb.clean(args.get("format")).lower() or "markdown"
    if fmt not in ("markdown", "html"):
        raise ValueError("I can build the kit as markdown or html.")
    text, suffix = (_kit_md(prof), ".md") if fmt == "markdown" else (_kit_html(prof), ".html")
    path = cb.write_file(settings, f"Media kit{suffix}", text)
    return screen.Shown(f"Built your media kit as {path.name} in the Creator business folder. Check the numbers are current before you share it.",
                        screen.file_card(settings, path))


def _draft(settings: Settings, title: str, lines: list[str], spoken: str) -> screen.Shown:
    text = "\n".join(lines)
    path = cb.write_file(settings, f"{title} (draft).md", text + "\n")
    return screen.Shown(f"{spoken} Saved as {path.name}. It's a draft; I have not sent anything.", screen.card(
        "text", title, f"creatorbiz-{path.stem}", text=text))


def _sign(settings: Settings) -> str:
    return _profile(settings).get("name") or "[Your name]"


def pitch_draft(settings: Settings, args: dict) -> screen.Shown:
    brand = cb.need(args.get("brand"), "brand")
    prof = _profile(settings)
    who = cb.clean(args.get("contact_name"), 60) or "team"
    idea = cb.clean(args.get("idea"), 400) or "[Describe your idea for the campaign]"
    stats = ", ".join(x for x in (prof.get("niche"), prof.get("platforms"), (f"around {prof['avg_views']:,} views per video"
                                                                            if prof.get("avg_views") else "")) if x)
    lines = [f"Subject: Collaboration idea for {brand}", "", f"Hi {who},", "",
             f"I'm {_sign(settings)}, a creator" + (f" ({stats})" if stats else "") + f". I really like what {brand} is doing"
             + (f", especially {cb.clean(args.get('why'), 200)}" if args.get("why") else "") + ".", "",
             f"My idea: {idea}", "",
             "I'd be happy to share my media kit and rates, and any paid partnership would be clearly labelled as an ad.",
             "Would you be open to a quick chat?", "", "Thanks,", _sign(settings)]
    return _draft(settings, f"Pitch to {brand}", lines, f"Here's a pitch email draft for {brand}.")


def followup_draft(settings: Settings, args: dict) -> screen.Shown:
    brand = cb.need(args.get("brand"), "brand")
    lines = [f"Subject: Following up - collaboration with {brand}", "", f"Hi {cb.clean(args.get('contact_name'), 60) or 'team'},", "",
             "I wanted to follow up on my earlier message in case it got buried. I'm still keen to work together"
             + (f" on {cb.clean(args.get('idea'), 200)}" if args.get("idea") else "") + ".", "",
             "If now isn't the right time, no problem at all; just let me know who's best to speak to.", "", "Thanks,", _sign(settings)]
    return _draft(settings, f"Follow-up to {brand}", lines, f"Here's a friendly follow-up draft for {brand}.")


def negotiation_draft(settings: Settings, args: dict) -> screen.Shown:
    brand = cb.need(args.get("brand"), "brand")
    fee = cb.gbp(cb.money(args.get("fee"), "counter fee")) if args.get("fee") else "[your fee]"
    lines = [f"Subject: Re: {brand} campaign offer", "", f"Hi {cb.clean(args.get('contact_name'), 60) or 'team'},", "",
             f"Thank you for the offer. Based on the scope, my fee for this campaign would be {fee}.", "",
             "That covers the deliverables as described. If you'd like usage in paid ads, exclusivity, or a faster turnaround, "
             "I'm happy to quote those separately.", "",
             "Could you also confirm payment terms and send the agreement so we can agree everything in writing?", "", "Thanks,",
             _sign(settings)]
    return _draft(settings, f"Reply to {brand} offer", lines, f"Here's a counter-offer draft for {brand}.")


def decline_draft(settings: Settings, args: dict) -> screen.Shown:
    brand = cb.need(args.get("brand"), "brand")
    reason = cb.clean(args.get("reason"), 200) or "it isn't the right fit for my content at the moment"
    lines = [f"Subject: Re: {brand} collaboration", "", f"Hi {cb.clean(args.get('contact_name'), 60) or 'team'},", "",
             f"Thank you for thinking of me. After looking at it, I'm going to pass this time because {reason}.", "",
             "I'd be glad to hear about future projects.", "", "Best wishes,", _sign(settings)]
    return _draft(settings, f"Decline {brand}", lines, f"Here's a polite decline for {brand}.")


def contract_checklist(settings: Settings, args: dict) -> screen.Shown:
    deal = cb.pick_deal(cb.deals(settings), args.get("brand"), args.get("campaign")) if args.get("brand") else None
    checks = deal.get("checks", {}) if deal else {}
    items = [{"key": k, "title": t, "help": h, "ticked": bool(checks.get(k))} for k, t, h in CHECKLIST]
    done = sum(i["ticked"] for i in items)
    title = f"Contract checklist: {cb.deal_label(deal)}" if deal else "Contract checklist"
    spoken = (f"{done} of {len(items)} contract points checked for {cb.deal_label(deal)}." if deal
              else f"Here are {len(items)} things to check before you sign a brand deal.")
    return screen.Shown(f"{spoken} {LEGAL}", screen.card(
        KIND, title, f"creatorbiz-checklist-{cb.deal_label(deal) if deal else 'general'}",
        data={"brand": deal["brand"] if deal else "", "items": items, "note": LEGAL + " Check current ASA/CMA guidance on #ad rules."},
        buttons=[{"label": "#ad rules", "say": "Explain #ad and disclosure rules for creators."}]))


def contract_tick(settings: Settings, args: dict) -> screen.Shown:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    key = cb.find([k for k, _, _ in CHECKLIST] + [t for _, t, _ in CHECKLIST], args.get("item"))
    if key is None:
        raise ValueError("Which checklist point? For example payment, usage, exclusivity or disclosure.")
    key = next((k for k, t, _ in CHECKLIST if key in (k, t)), key)
    d.setdefault("checks", {})[key] = args.get("ticked", True) is not False
    cb.save(settings, cb.DEALS, deals)
    return contract_checklist(settings, {"brand": d["brand"], "campaign": d.get("campaign")})


def guide(name: str) -> screen.Shown:
    title, lines = GUIDES[name]
    return screen.Shown(f"{title}: {lines[0]} {lines[-1]}", screen.card(
        "list", title, f"creatorbiz-{name}", items=[{"label": line} for line in lines],
        buttons=[{"label": "Contract checklist", "say": "Show me the contract checklist."}]))


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_docs",
        "description": "Creator paperwork and guides: save media kit details and build the media kit as a Markdown or HTML file; "
                       "draft (never send) pitch, follow-up, counter-offer and decline emails to brands; a contract checklist "
                       "to tick per deal; plain-words UK guides on #ad disclosure rules, usage rights, exclusivity, payment terms, "
                       "questions to ask brands, red flags, tax basics and negotiating. General information, not legal or tax advice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "brand": {"type": "string"},
                "campaign": {"type": "string"},
                "contact_name": {"type": "string"},
                "idea": {"type": "string", "description": "The campaign idea for a pitch."},
                "why": {"type": "string", "description": "What the creator likes about the brand."},
                "fee": {"type": "number", "description": "Counter-offer fee in pounds."},
                "reason": {"type": "string"},
                "item": {"type": "string", "description": "Checklist point: scope, fee, payment, usage, exclusivity, disclosure, "
                         "approval, deadlines, cancellation, ownership, ads_access or claims."},
                "ticked": {"type": "boolean"},
                "format": {"type": "string", "enum": ["markdown", "html"]},
                "name": {"type": "string"}, "niche": {"type": "string"}, "bio": {"type": "string"},
                "audience": {"type": "string", "description": "Who watches, as the user says."},
                "platforms": {"type": "string", "description": "e.g. 'TikTok 12k, Instagram 4k' as the user says."},
                "avg_views": {"type": "integer"},
                "past_work": {"type": "string"}, "services": {"type": "string"},
                "contact": {"type": "string"}, "pay_to": {"type": "string", "description": "Payment details for invoices."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    handlers = {"kit_set": kit_set, "kit_build": kit_build, "pitch_draft": pitch_draft, "followup_draft": followup_draft,
                "negotiation_draft": negotiation_draft, "decline_draft": decline_draft,
                "contract_checklist": contract_checklist, "contract_tick": contract_tick}
    if action in handlers:
        return handlers[action](settings, args)
    if action in GUIDES:
        return guide(action)
    return kit_show(settings)
