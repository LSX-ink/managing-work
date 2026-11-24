"""Contact sections: the "Find us" block at the bottom of a small-business site, with one-tap ways to get in touch.

make_contact_section turns the business's details into a paste-in HTML block in the brand colour: big tap-friendly
buttons for Call, WhatsApp, Email and Get directions (the directions button opens Google Maps or Apple Maps on the
visitor's phone, with no map embedded, so the page stays fast and sends nothing to Google until they tap), the address
written out for people and search engines (schema.org LocalBusiness with address, phone, email and opening hours text
if given), a short line of when to reach them, and social links. Phone numbers become proper tel: links in the
international form when a country code is given. Nothing needs JavaScript and every colour pair passes WCAG AA.
Saves contact.html and contact-preview.html in Kinetic Web Designs/<name>/web.
"""

import html
import json
import re
from urllib.parse import quote

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_palette import on

NAMES = {"make_contact_section"}
CODES = {"GB": "44", "ZA": "27", "US": "1", "CA": "1", "AU": "61", "NZ": "64", "IE": "353", "DE": "49", "FR": "33",
         "ES": "34", "IT": "39", "NL": "31", "IN": "91", "NG": "234", "KE": "254", "AE": "971"}
SOCIALS = {"instagram": ("Instagram", "https://instagram.com/{}"), "facebook": ("Facebook", "https://facebook.com/{}"),
           "tiktok": ("TikTok", "https://www.tiktok.com/@{}"), "linkedin": ("LinkedIn",
                                                                         "https://www.linkedin.com/company/{}")}


def phone_link(phone: str, country: str) -> str:
    """'0121 496 0000' with GB -> '+441214960000'; numbers already starting + are kept."""
    digits = re.sub(r"[^\d+]", "", phone)
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not digits.startswith("+") and country:
        digits = "+" + CODES[country] + digits.lstrip("0")
    if len(re.sub(r"\D", "", digits)) < 7:
        raise ValueError("That phone number looks too short.")
    return digits


def block(d: dict) -> str:
    e = html.escape
    brand = d["brand"]
    button = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    buttons = []
    if d["phone"]:
        buttons.append(("Call", f"tel:{d['phone_link']}", d["phone"]))
    if d["whatsapp"]:
        buttons.append(("WhatsApp", f"https://wa.me/{d['whatsapp'].lstrip('+')}", "Message us"))
    if d["email"]:
        buttons.append(("Email", f"mailto:{d['email']}", d["email"]))
    if d["address"]:
        buttons.append(("Get directions", "https://www.google.com/maps/search/?api=1&query="
                        + quote(f"{d['name']}, {', '.join(d['address'])}"), "Opens your maps app"))
    new_tab = ' target="_blank" rel="noopener"'
    btns = "\n".join(
        f'    <a class="c-btn{" main" if i == 0 else ""}" href="{e(url)}"'
        f'{new_tab if url.startswith("https://") else ""}>'
        f"<strong>{e(label)}</strong><span>{e(sub)}</span></a>" for i, (label, url, sub) in enumerate(buttons))
    lines = "<br>".join(e(x) for x in d["address"])
    addr = f'<address><strong>{e(d["name"])}</strong><br>{lines}</address>' if d["address"] else ""
    when = f'<p class="c-when">{e(d["hours"])}</p>' if d["hours"] else ""
    soc = " ".join(f'<a href="{e(u)}" target="_blank" rel="noopener">{e(label)}</a>' for label, u in d["socials"])
    data = {"@context": "https://schema.org", "@type": "LocalBusiness", "name": d["name"]}
    if d["address"]:
        data["address"] = {"@type": "PostalAddress", "streetAddress": ", ".join(d["address"])}
        if d["country"]:
            data["address"]["addressCountry"] = d["country"]
    if d["phone"]:
        data["telephone"] = d["phone_link"]
    if d["email"]:
        data["email"] = d["email"]
    if d["hours"]:
        data["description"] = d["hours"]
    if d["socials"]:
        data["sameAs"] = [u for _, u in d["socials"]]
    ld = json.dumps(data, indent=2, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!-- Contact section for {e(d["name"])}: paste this block where people should find you. -->
<section class="contact" aria-labelledby="c-title"
         style="--c-brand:{button};--c-on:{on(button)};--c-accent:{accent}">
  <style>
    .contact {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #18181b;
               max-width: 60rem; margin: 0 auto; padding: 0 1rem; }}
    .contact h2 {{ font-size: clamp(1.75rem, 4.5vw, 2.5rem); margin: 0 0 .5rem; }}
    .contact .c-intro {{ color: #52525b; margin: 0 0 1.5rem; }}
    .c-grid {{ display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
              align-items: start; }}
    .c-btns {{ display: grid; gap: .75rem; }}
    .c-btn {{ display: flex; flex-direction: column; justify-content: center; min-height: 56px; padding: .6rem 1.1rem;
             border-radius: 1rem; border: 2px solid var(--c-accent); color: var(--c-accent); background: #fff;
             text-decoration: none; }}
    .c-btn span {{ color: #52525b; font-size: .9rem; overflow-wrap: anywhere; }}
    .c-btn.main {{ background: var(--c-brand); border-color: var(--c-brand); color: var(--c-on); }}
    .c-btn.main span {{ color: inherit; opacity: .9; }}
    .c-btn:focus-visible, .c-social a:focus-visible {{ outline: 3px solid var(--c-accent); outline-offset: 3px; }}
    .contact address {{ font-style: normal; line-height: 1.7; padding: 1.25rem; border-radius: 1rem;
                       background: #f4f4f5; }}
    .c-when {{ margin: 1rem 0 0; color: #3f3f46; }}
    .c-social {{ margin: 1rem 0 0; display: flex; gap: 1rem; flex-wrap: wrap; }}
    .c-social a {{ color: var(--c-accent); font-weight: 600; }}
  </style>
  <h2 id="c-title">{e(d["title"])}</h2>
  {f'<p class="c-intro">{e(d["intro"])}</p>' if d["intro"] else ''}
  <div class="c-grid">
    <div class="c-btns">
{btns}
    </div>
    <div>
      {addr}
      {when}
      {f'<p class="c-social">{soc}</p>' if soc else ''}
    </div>
  </div>
  <script type="application/ld+json">
{ld}
  </script>
</section>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the contact section.")
    brand = colour(args.get("colour") or "")
    country = clean(args.get("country")).upper()
    if country and country not in CODES:
        raise ValueError(f"Country can be {', '.join(CODES)} (it sets the phone code).")
    phone = clean(args.get("phone"))
    whatsapp = phone_link(clean(args.get("whatsapp")), country) if clean(args.get("whatsapp")) else ""
    if whatsapp and not whatsapp.startswith("+"):
        raise ValueError("Give the WhatsApp number with its country code (or set the country).")
    email = clean(args.get("email"))
    if email and not re.fullmatch(r"[^\s@<>\"']+@[^\s@<>\"']+\.[^\s@<>\"']+", email):
        raise ValueError("That email address doesn't look right.")
    raw = args.get("address") or []
    lines = [clean(x) for x in (raw if isinstance(raw, list) else str(raw).split(","))]
    lines = [x for x in lines if x][:6]
    socials = []
    for key, value in (args.get("socials") or {}).items():
        if key.lower() not in SOCIALS:
            raise ValueError(f"Socials can be {', '.join(SOCIALS)}.")
        handle = clean(value).lstrip("@")
        if handle and not re.fullmatch(r"[\w.-]{1,60}", handle):
            raise ValueError(f"'{handle[:40]}' doesn't look like a {SOCIALS[key.lower()][0]} handle.")
        if handle:
            socials.append((SOCIALS[key.lower()][0], SOCIALS[key.lower()][1].format(handle)))
    if not (phone or whatsapp or email or lines):
        raise ValueError("Give at least one way to get in touch: phone, WhatsApp, email or address.")
    d = {"name": name, "brand": brand, "country": country, "phone": phone,
         "phone_link": phone_link(phone, country) if phone else "", "whatsapp": whatsapp, "email": email,
         "address": lines, "hours": clean(args.get("hours"))[:120], "socials": socials,
         "title": clean(args.get("title")) or "Get in touch", "intro": clean(args.get("intro"))[:200]}
    code = block(d)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Contact</title>\n"
               "</head>\n<body style=\"margin:0;padding:56px 0;background:#fff\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "contact.html").write_text(code, encoding="utf-8")
    (path / "contact-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    ways = [w for w, v in (("call", phone), ("WhatsApp", whatsapp), ("email", email), ("directions", lines)) if v]
    return (f"Made a contact section for {name} in {where}: contact.html to paste into the page and "
            f"contact-preview.html to check it, with one-tap {', '.join(ways)}. The directions button opens the "
            "visitor's maps app; no map is embedded, so the page stays fast. Check the phone number and address "
            "carefully before it goes live.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_contact_section",
        "description": "Make a paste-in 'Get in touch / Find us' section for a website in the brand colour: big "
                       "one-tap Call, WhatsApp, Email and Get directions buttons (opens the maps app, no embedded "
                       "map), the address, when to reach them, social links, and schema.org LocalBusiness data. No "
                       "JavaScript, AA contrast. Saves contact.html and a preview in Kinetic Web Designs/<name>/web. "
                       "Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "country": {"type": "string", "enum": list(CODES), "description": "Sets the phone code, e.g. GB."},
                "phone": {"type": "string"},
                "whatsapp": {"type": "string", "description": "WhatsApp number (with country code or country)."},
                "email": {"type": "string"},
                "address": {"type": "array", "items": {"type": "string"},
                            "description": "Lines, e.g. ['21 Hockley Hill', 'Birmingham', 'B18 5BW']."},
                "hours": {"type": "string", "description": "e.g. 'Mon-Sat 9am-5:30pm'."},
                "socials": {"type": "object", "properties": {k: {"type": "string"} for k in SOCIALS}},
                "title": {"type": "string", "description": "Heading (default 'Get in touch')."},
                "intro": {"type": "string"},
            },
            "required": ["name", "colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
