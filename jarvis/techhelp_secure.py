"""Tech helper, staying safe: a local password-strength checker, a phishing-sign spotter for pasted messages, and the
two-factor and backup checklists.

The password is typed into the pop-up and measured in the browser, so it never reaches Alfred or chat. The phishing
check uses fixed rules on the text you paste and does not open any link or go online.
"""

import re
from urllib.parse import urlparse

import homestore as hs
import screen
import techhelp_data as data
import techhelp_store as store
from config import Settings

ACTIONS = ["password_check", "phish_check", "checklist_show", "checklist_tick", "checklist_reset"]

COMMON = {"password", "passw0rd", "letmein", "welcome", "admin", "qwerty", "abc123", "iloveyou", "monkey", "dragon",
          "football", "baseball", "master", "sunshine", "princess", "login", "starwars", "shadow", "superman",
          "trustno1", "changeme", "liverpool", "arsenal", "chelsea", "manchester", "london", "summer", "winter",
          "freedom", "whatever", "hello", "michael", "charlie", "ashley", "jordan", "harry", "welcome1", "secret"}
WALKS = ("qwerty", "asdfg", "zxcvb", "qazwsx", "1qaz", "poiuy", "lkjhg", "azerty")
RATE = 1e10  # guesses a second for a fast attacker with a stolen, weakly protected password list


def tool_definitions() -> list[dict]:
    return [{
        "name": "techhelp_secure",
        "description": "Stay safe online. password_check pops up a private strength meter: the user types the "
                       "password into it and it is measured in the browser only; never ask for, repeat or accept "
                       "a password in chat. phish_check (text: "
                       "the pasted email, text or link) lists scam signs with local rules only, no links opened. "
                       "checklist_show (list: 2fa or backup) pops up a clickable checklist, checklist_tick (step "
                       "number; leave out for the current step; done false unticks), checklist_reset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "text": {"type": "string", "description": "phish_check: the message or link to check."},
                "list": {"type": "string", "enum": list(data.LISTS)},
                "step": {"type": "integer"},
                "done": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"techhelp_secure"}


# ---- password strength (measured in the pop-up, see popup-techhelp.js) -------------------------------

def password_check(args: dict) -> screen.Shown:
    """Pop up the meter; the password is typed into the pop-up and measured there, so it never reaches chat."""
    data_ = {"common": sorted(COMMON), "walks": list(WALKS), "rate": RATE}
    return screen.Shown("Type the password into the box on screen. It's checked on this PC only and never sent to me.",
                        screen.card("techhelp-meter", "Password strength", "techhelp-password", data=data_,
                                    buttons=[{"label": "2FA checklist", "say": "Show me the two-factor checklist."}]))


# ---- phishing signs -------------------------------------------------------------------------

BRANDS = {"paypal": ["paypal.com", "paypal.co.uk"], "apple": ["apple.com", "icloud.com"],
          "amazon": ["amazon.co.uk", "amazon.com"], "hmrc": ["gov.uk"], "royalmail": ["royalmail.com"],
          "evri": ["evri.com"], "dpd": ["dpd.co.uk", "dpd.com"], "netflix": ["netflix.com"],
          "barclays": ["barclays.co.uk", "barclays.com"], "lloyds": ["lloydsbank.com", "lloydsbank.co.uk"],
          "natwest": ["natwest.com"], "hsbc": ["hsbc.co.uk", "hsbc.com"], "santander": ["santander.co.uk"],
          "microsoft": ["microsoft.com", "live.com"], "google": ["google.com"], "dhl": ["dhl.com", "dhl.co.uk"]}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly", "rb.gy", "shorturl.at"}
BAD_TLDS = (".xyz", ".top", ".click", ".icu", ".buzz", ".shop", ".live", ".cfd", ".sbs", ".rest", ".zip")
RULES = [
    (r"urgent|immediately|within \d+ (?:hours?|minutes)|final (?:notice|warning)|last chance|act now|expires? today",
     2, "Pressure to act fast"),
    (r"suspend|locked|deactivat|unusual (?:activity|sign)|security alert|verify your|confirm your (?:identity|account|details)",
     2, "Says your account is at risk"),
    (r"password|pin\b|passcode|one[- ]time (?:code|passcode)|security code|card number|cvv|sort code|bank details|login details",
     3, "Asks for secret details"),
    (r"gift ?cards?|bitcoin|crypto|western union|wire transfer|itunes card|voucher",
     3, "Asks for payment in gift cards, crypto or transfers"),
    (r"you(?:'ve| have)? won|prize|lottery|winner|claim your|free (?:gift|iphone|reward)|congratulations",
     3, "Offers a prize or reward"),
    (r"refund|tax rebate|unpaid|overdue|penalty|fine of|arrears", 2, "Talks about a refund, debt or penalty"),
    (r"parcel|delivery|redeliver|customs|missed (?:a )?delivery|delivery fee|shipping fee", 2, "Parcel or delivery fee"),
    (r"\bhi (?:mum|dad)\b|new number|lost my phone|broken phone", 3, "'Hi Mum' style message from a new number"),
    (r"dear (?:customer|user|client|member|account holder)|valued customer", 1, "Doesn't use your name"),
    (r"do not (?:tell|share)|keep this (?:secret|confidential)|don't tell", 2, "Asks you to keep it secret"),
    (r"attached|attachment|open the file|enable (?:macros|content)|\.(?:zip|exe|scr|html?|iso|docm|xlsm)\b",
     2, "Pushes you to open an attachment"),
    (r"click (?:here|the link|below)|tap (?:here|the link)|follow (?:this|the) link|log ?in (?:here|now)",
     1, "Wants you to click a link"),
]


def _links(text: str) -> list[str]:
    return re.findall(r"(?:https?://|www\.)[^\s<>\"')]+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}/[^\s<>\"')]*", text, re.I)


def _host(link: str) -> str:
    url = link if "//" in link else "//" + link
    return (urlparse(url).hostname or "").lower()


def _link_flags(link: str) -> list[str]:
    host, out = _host(link), []
    if not host:
        return out
    if re.fullmatch(r"[\d.]+", host):
        out.append("A link goes to a bare number address")
    if host in SHORTENERS:
        out.append(f"A shortened link ({host}) hides where it goes")
    if "xn--" in host:
        out.append("A link uses look-alike foreign letters")
    if "@" in link.split("//")[-1].split("/")[0]:
        out.append("A link has an @ that disguises its real destination")
    if host.endswith(BAD_TLDS):
        out.append(f"A link ends in {host[host.rfind('.'):]}, common in scam sites")
    if link.lower().startswith("http://"):
        out.append("A link isn't secure (http, not https)")
    if host.count(".") >= 4 or host.count("-") >= 3:
        out.append("A link has an unusually long, tangled address")
    flat = host.translate(str.maketrans("10", "lo")).replace("-", "")
    for brand, real in BRANDS.items():
        if brand in flat and not any(host == r or host.endswith("." + r) for r in real):
            out.append(f"A link mentions {brand.title()} but isn't its real site")
            break
    return out


def phish_check(args: dict) -> screen.Shown:
    text = str(args.get("text") or "").strip()
    if not text:
        raise ValueError("Paste the message or link you want me to check.")
    text = text[:5000]
    flags, score = [], 0
    for pattern, weight, why in RULES:
        if re.search(pattern, text, re.I):
            flags.append(why)
            score += weight
    for link in _links(text) or ([text] if re.fullmatch(r"\S+\.\S+", text) else []):
        found = _link_flags(link)
        flags += [f for f in found if f not in flags]
        score += 3 * len(found)
    verdict = ("looks very like a scam" if score >= 7 else "has some warning signs" if score >= 3
               else "shows no obvious scam signs, but stay careful")
    advice = ("Don't click links or open attachments. Go to the company's own app or type its address yourself. "
              "Forward scam texts to 7726 and scam emails to report@phishing.gov.uk.") if score >= 3 else \
        "If in doubt, contact the sender through their official app or phone number, not this message."
    rows = [[f, "Warning sign"] for f in flags] or [["Nothing obvious found", "The rules didn't match"]]
    said = f"That message {verdict}. " + (f"Main signs: {'; '.join(flags[:3])}. " if flags else "") + advice
    return screen.Shown(said, screen.card(
        "table", "Scam check", "techhelp-phish", columns=["What I noticed", ""], rows=rows,
        text=f"Verdict: it {verdict}.\n{advice}"))


# ---- checklists -------------------------------------------------------------------------------

def _list(name) -> tuple[str, str, list]:
    text = hs.need(name, "checklist").lower()
    for key, (title, steps) in data.LISTS.items():
        if text in (key, title.lower()) or key in text or ("two" in text and key == "2fa"):
            return key, title, steps
    raise ValueError("I have a two-factor checklist (2fa) and a backup checklist.")


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "password_check":
        return password_check(args)
    if action == "phish_check":
        return phish_check(args)
    if action in ("checklist_show", "checklist_tick", "checklist_reset"):
        key, title, steps = _list(args.get("list"))
        about, pid = f"the {title}", f"list-{key}"
        if action == "checklist_show":
            return store.show(settings, pid, title, steps, about)
        if action == "checklist_reset":
            return store.reset(settings, pid, title, steps, about)
        return store.tick(settings, pid, title, steps, about, args.get("step"), args.get("done") is not False)
    raise ValueError(f"Unknown action {action}.")
