"""Scam and red-flag help for "get rich" offers: paste an offer and see which warning signs it has (MLM, upfront fees,
crypto giveaways, fake cheques, task scams), plain-words explanations, a before-you-pay checklist, what to do if you've
been caught out, and MLM maths using the numbers you're quoted.

The checker only reads the text you give it, on this PC; it is a quick check, not proof either way. Results pop up as
"sidehustle-redflags" or "sidehustle-calc" (frontend/popup-sidehustle.js). General guidance; check GOV.UK for current advice.
"""

import re

import screen
import sidehustle_data as data
import sidehustle_store as st
from config import Settings

NAMES = {"sidehustle_safety"}
ACTIONS = ["check_offer", "red_flag_guide", "scam_types", "explain_scam", "before_you_pay", "if_scammed", "mlm_math",
           "verify_company", "legit_signs"]
LEVELS = [(8, "very likely a scam or a scheme that loses most people money"), (4, "several serious warning signs"),
          (1, "a few things to check first"), (0, "no obvious red flags in the words, which isn't proof it's genuine")]
BEFORE_PAY = ["Have I been asked to pay anything before I can earn? If yes, stop.",
              "Can I find independent reviews (not on their own site) that mention losing money?",
              "Is the company on Companies House, with a real address and named directors?",
              "If it involves investing or credit, is the firm on the Financial Conduct Authority register?",
              "Am I being rushed? A genuine offer will still be there tomorrow.",
              "Will I pay by card or PayPal, which have protection, not gift cards, transfers or crypto?",
              "Did I ask what the average person earns after costs, and did I get a straight answer?",
              "Have I told a friend about it and listened to what they said?"]
IF_SCAMMED = ["Stop all contact and don't send any more money, even to 'get your money back'.",
              "Tell your bank or card company straight away; you can phone 159 to reach many UK banks. Ask about getting money back.",
              "Report it to the police fraud reporting service (Action Fraud, or its newer replacement; check GOV.UK for how).",
              "Forward scam texts to 7726 and scam emails to report@phishing.gov.uk.",
              "Change any passwords you shared and check your credit file for unfamiliar accounts.",
              "Expect 'recovery' scammers to contact you next; never pay anyone to get money back.",
              "Free help and support: Citizens Advice, and your bank's fraud team. It isn't your fault."]
LEGIT = ["You never pay to start earning; costs are clear, small and optional.",
         "They explain how you get paid, when, and by whom.",
         "Income comes from real customers buying, not from recruiting people.",
         "You can leave freely, with the refund terms written down.",
         "The company has a checkable address, a Companies House entry and independent reviews.",
         "They give honest ranges (including 'many people earn little') and no guarantees."]
VERIFY = ["Search the company name on Companies House (free, GOV.UK) and check its age, address and directors.",
          "For investing, trading or credit, look the firm up on the Financial Conduct Authority register and its warning list.",
          "Search the name with the words scam, complaints and reviews; ignore reviews on the seller's own site.",
          "Check the website age with a public 'whois' lookup: very new sites making big claims are risky.",
          "Phone the company using a number you found yourself, not one they messaged you.",
          "Ask for the terms, refund policy and any earnings disclosure in writing."]


def check_offer(settings: Settings, args: dict):
    text = st.need(args.get("text"), "offer text to check", 4000)
    low = text.lower()
    found = [(w, label, why) for pattern, w, label, why in data.FLAG_RULES if re.search(pattern, low)]
    score = sum(w for w, _, _ in found)
    level = next(label for floor, label in LEVELS if score >= floor)
    advice = ["Don't pay, share bank details or send documents until you've checked it.", "This is a quick text check, not proof either way."]
    say = (f"That offer shows {len(found)} warning sign{'s' if len(found) != 1 else ''}: {level}." if found
           else "I found no obvious red flags in the words, but that isn't proof it's genuine.")
    return screen.Shown(say, screen.card(st.FLAGS, "Offer red-flag check", "", data={
        "score": score, "level": level, "flags": [{"label": label, "why": why} for _, label, why in found],
        "excerpt": text[:160], "advice": advice},
        buttons=[{"label": "Before I pay", "say": "Give me the before-you-pay checklist."},
                 {"label": "If I've paid", "say": "What should I do if I've been scammed?"}]))


def red_flag_guide(settings: Settings, args: dict):
    seen = {}
    for _, _, label, why in data.FLAG_RULES:
        seen[label] = why
    return screen.Shown("Here are the warning signs to look for in get-rich offers.", screen.card(
        st.FLAGS, "Red flags in get-rich offers", "", data={"score": None, "level": "", "flags": [
            {"label": k, "why": v} for k, v in seen.items()], "excerpt": "", "advice": [
            "If you see one or two, slow down. If you see several, walk away."]},
        buttons=[{"label": "Check an offer", "say": "Check this offer for red flags."}]))


def scam_types(settings: Settings, args: dict):
    items = [{"label": f"{v[0]}: {v[1]}", "say": f"Explain the {v[0]} scam."} for v in data.SCAMS.values()]
    return screen.Shown(f"There are {len(items)} common ones. Tap one to hear more.", screen.card(
        "list", "Common get-rich scams", "sidehustle-scams", items=items))


def _scam(name: str) -> tuple:
    key = st.clean(name).lower()
    for k, v in data.SCAMS.items():
        if key in (k, v[0].lower()) or (key and (key in v[0].lower() or k in key)):
            return v
    words = {"pyramid": "mlm", "network": "mlm", "multi": "mlm", "fee": "upfront", "bitcoin": "crypto", "giveaway": "crypto",
             "overpay": "cheque", "check": "cheque", "like": "task", "boost": "task", "forex": "trading", "bot": "trading",
             "dropship": "course", "coach": "course", "guru": "course"}
    for w, k in words.items():
        if w in key:
            return data.SCAMS[k]
    raise ValueError("I don't know that one. Ask me for the list of common scams.")


def explain_scam(settings: Settings, args: dict):
    title, what, signs, action = _scam(st.need(args.get("scam_type"), "scam type"))
    return st.calc(f"{title}: {what} {action}", title, title, what, [("Warning sign", s) for s in signs],
                   ["What to do: " + action, "General guidance; check GOV.UK for current advice."],
                   buttons=[{"label": "Check an offer", "say": "Check this offer for red flags."}])


def _list(title: str, items: list[str], text: str, done: bool = False):
    return screen.Shown(text, screen.card("list", title, "", items=[{"label": i, "done": done} for i in items]))


def before_you_pay(settings: Settings, args: dict):
    return _list("Before you pay anything", BEFORE_PAY, "Here is your before-you-pay checklist; one 'no' is a reason to stop.")


def if_scammed(settings: Settings, args: dict):
    return _list("If you've been scammed", IF_SCAMMED, "Don't panic; here are the steps. It isn't your fault.")


def verify_company(settings: Settings, args: dict):
    return _list("Checking a company", VERIFY, "Here's how to check a company out; I haven't looked anything up for you.")


def legit_signs(settings: Settings, args: dict):
    return _list("Signs an opportunity is more likely genuine", LEGIT, "These are signs of a more genuine offer; none is a guarantee.", True)


def mlm_math(settings: Settings, args: dict):
    join = st.number(args.get("joining_cost"), "joining cost", allow_zero=True)
    monthly_cost = st.number(args.get("monthly_cost", 0), "monthly cost", allow_zero=True)
    earn = st.number(args.get("monthly_earnings"), "monthly earnings you were promised", allow_zero=True)
    months = int(args.get("months") or 12)
    if not 1 <= months <= 60:
        raise ValueError("Give months between 1 and 60.")
    net = earn - monthly_cost
    year = round(net * months - join, 2)
    if net <= 0:
        back = "never at those numbers"
    else:
        back = f"about {-(-join // net):.0f} months" if join else "straight away"
    rows = [("Joining cost", st.gbp(join)), ("Monthly costs (stock, fees)", st.gbp(monthly_cost)), ("Monthly earnings claimed", st.gbp(earn)),
            (f"Position after {months} months", st.gbp(year)), ("Time to get joining cost back", back)]
    notes = ["Ask for the official average member's earnings after costs; most such schemes report that most members earn little or lose money.",
             "Use the real average, not the best story you were shown.", st.HONEST]
    return st.calc(f"On those numbers you'd be {st.gbp(abs(year))} {'ahead' if year >= 0 else 'behind'} after {months} months. "
                   "Real results are usually lower than sales claims.", "MLM maths", st.gbp(year), f"after {months} months, if the claimed earnings were true",
                   rows, notes)


def tool_definitions() -> list[dict]:
    return [{
        "name": "sidehustle_safety",
        "description": "Scam and red-flag help for get-rich-quick, MLM, upfront-fee, crypto giveaway, fake cheque and task job offers: "
                       "check a pasted offer for warning signs, red flag guide, list and explain common scams in plain words, "
                       "before-you-pay checklist, what to do if scammed, MLM maths from quoted numbers, how to verify a company, "
                       "signs of a genuine opportunity. General guidance, nothing is sent anywhere.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "text": {"type": "string", "description": "The offer, message or advert text to check."},
                "scam_type": {"type": "string", "description": "e.g. MLM, upfront fee, crypto giveaway, fake cheque, task scam, trading bot, course."},
                "joining_cost": {"type": "number"}, "monthly_cost": {"type": "number"},
                "monthly_earnings": {"type": "number"}, "months": {"type": "integer"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"check_offer": check_offer, "red_flag_guide": red_flag_guide, "scam_types": scam_types,
                "explain_scam": explain_scam, "before_you_pay": before_you_pay, "if_scammed": if_scammed,
                "mlm_math": mlm_math, "verify_company": verify_company, "legit_signs": legit_signs}
    action = args.get("action")
    if action not in handlers:
        raise ValueError("What would you like to check? " + ", ".join(ACTIONS))
    return handlers[action](settings, args)
