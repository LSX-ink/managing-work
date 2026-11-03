"""Email signatures: a neat branded sign-off for the bottom of every email, that pastes cleanly into Gmail and Outlook.

make_email_signature builds the signature the way email apps need it: a small table with the styles on each tag, the
initials tile (or a logo picture link) in the brand colour, the person's name and job, the business, then phone, email,
website and up to four social links as plain text links (no icons, so nothing is blocked or shows as a broken
picture). Colours are checked so every line reads on white, and links get the tel: and mailto: forms so they work
with one tap on a phone. It saves signature.html (open it in a browser, select all, copy and paste into the email
app's signature settings) and signature.txt for plain-text emails, in Kinetic Web Designs/<name>/email.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_logo import initials
from design_palette import on

NAMES = {"make_email_signature"}
FONT = "Arial, Helvetica, sans-serif"  # the fonts every email app has
INK, MUTED = "#18181b", "#52525b"
SOCIALS = {"instagram": "Instagram", "tiktok": "TikTok", "facebook": "Facebook", "linkedin": "LinkedIn", "x": "X",
           "youtube": "YouTube"}
MAX_SOCIALS = 4


def https(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        return ""
    if re.match(r"(?i)^https://[^\s/]+\.[^\s/]+(/\S*)?$", url):
        return url
    if re.match(r"(?i)^(www\.)?[\w-]+(\.[\w-]+)+(/\S*)?$", url):
        return "https://" + url
    raise ValueError(f"'{url}' isn't a web address; use something like lebosbakery.co.uk.")


def tel(phone: str) -> str:
    digits = re.sub(r"[^\d+]", "", phone)
    if len(re.sub(r"\D", "", digits)) < 6:
        raise ValueError("That phone number looks too short.")
    return "tel:" + digits


def email_link(address: str) -> str:
    if not re.fullmatch(r"[^\s@<>\"]+@[^\s@<>\"]+\.[^\s@<>\"]+", address):
        raise ValueError(f"'{address}' isn't an email address.")
    return "mailto:" + address


def social_links(socials: dict) -> list[tuple[str, str]]:
    if not isinstance(socials, dict):
        raise ValueError("Give socials as names and links, e.g. instagram: instagram.com/lebosbakery.")
    out = []
    for key, value in socials.items():
        key = str(key).strip().lower()
        if key not in SOCIALS:
            raise ValueError(f"Use these socials: {', '.join(SOCIALS)}.")
        if value:
            out.append((SOCIALS[key], https(str(value))))
    if len(out) > MAX_SOCIALS:
        raise ValueError(f"Pick up to {MAX_SOCIALS} socials; more makes the signature busy.")
    return out


def build(d: dict) -> str:
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    brand = d["brand"]
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)  # links and the name line read
    if d["logo"]:
        mark = (f'<img src="{e(d["logo"])}" width="64" alt="{e(d["business"])}" style="display:block;border:0;'
                f'width:64px;max-width:64px;height:auto;">')
    else:
        mark = (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td width="56" '
                f'height="56" align="center" valign="middle" bgcolor="{brand}" style="width:56px;height:56px;'
                f'border-radius:12px;background:{brand};font-family:{FONT};font-size:22px;font-weight:bold;'
                f'color:{on(brand)};">{e(d["mark"])}</td></tr></table>')
    line = f"font-family:{FONT};font-size:13px;line-height:20px;color:{MUTED};"
    link = f"color:{accent};text-decoration:none;"
    rows = [f'<div style="font-family:{FONT};font-size:16px;line-height:22px;font-weight:bold;color:{INK};">'
            f'{e(d["person"] or d["business"])}</div>']
    sub = " · ".join(e(x) for x in (d["role"], d["business"] if d["person"] else "") if x)
    if sub:
        rows.append(f'<div style="{line}">{sub}</div>')
    contact = []
    if d["phone"]:
        contact.append(f'<a href="{e(tel(d["phone"]))}" style="{link}">{e(d["phone"])}</a>')
    if d["email"]:
        contact.append(f'<a href="{e(email_link(d["email"]))}" style="{link}">{e(d["email"])}</a>')
    if d["website"]:
        shown = re.sub(r"^https://(www\.)?", "", d["website"]).rstrip("/")
        contact.append(f'<a href="{e(d["website"])}" style="{link}">{e(shown)}</a>')
    if contact:
        rows.append(f'<div style="{line}padding-top:6px;">' + " &nbsp;|&nbsp; ".join(contact) + "</div>")
    if d["socials"]:
        rows.append(f'<div style="{line}">' + " &nbsp;·&nbsp; ".join(
            f'<a href="{e(url)}" style="{link}font-weight:bold;">{e(label)}</a>' for label, url in d["socials"])
            + "</div>")
    if d["note"]:
        rows.append(f'<div style="{line}font-size:12px;padding-top:6px;">{e(d["note"])}</div>')
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Email signature</title></head>"
            "<body style=\"margin:0;padding:24px;background:#ffffff;\">\n"
            "<!-- Select everything below, copy, and paste it into the email app's signature settings. -->\n"
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">'
            f'<tr><td valign="top" style="padding:0 14px 0 0;">{mark}</td>'
            f'<td valign="top" style="padding:0 0 0 14px;border-left:3px solid {brand};">'
            + "".join(rows) + "</td></tr></table>\n</body></html>\n")


def plain(d: dict) -> str:
    lines = ["--", d["person"] or d["business"]]
    sub = " | ".join(x for x in (d["role"], d["business"] if d["person"] else "") if x)
    lines += [sub] if sub else []
    lines += [x for x in (d["phone"], d["email"], re.sub(r"^https://", "", d["website"])) if x]
    lines += [f"{label}: {url}" for label, url in d["socials"]]
    lines += [d["note"]] if d["note"] else []
    return "\n".join(lines) + "\n"


def run(settings: Settings, args: dict) -> str:
    clean = lambda k: " ".join(str(args.get(k) or "").split())  # noqa: E731
    business = clean("business")
    if not business:
        raise ValueError("Give the business name for the signature.")
    d = {"business": business, "brand": colour(args.get("colour") or ""), "person": clean("person"),
         "role": clean("role"), "phone": clean("phone"), "email": clean("email"),
         "website": https(clean("website")), "logo": https(clean("logo_url")),
         "socials": social_links(args.get("socials") or {}), "note": clean("note")[:160]}
    if not any(d[k] for k in ("phone", "email", "website")) and not d["socials"]:
        raise ValueError("Add at least one way to reach them: phone, email, website or a social link.")
    if d["email"]:
        email_link(d["email"])
    if d["phone"]:
        tel(d["phone"])
    d["mark"] = initials(business, clean("initials"))
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(business, 'folder name')}/email", create=True)
    name = memory.safe_name(clean("person") or "signature", "file name").lower().replace(" ", "-")
    name = "signature" if name == "signature" else f"signature-{name}"
    (path / f"{name}.html").write_text(build(d), encoding="utf-8")
    (path / f"{name}.txt").write_text(plain(d), encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made {name}.html and {name}.txt for {d['person'] or business} in {where}. Open the .html in a browser, "
            "select all, copy and paste it into the signature settings (Gmail: Settings, See all settings, "
            "Signature; Outlook: Settings, Mail, Compose and reply). Phone and email are tap-to-call and "
            "tap-to-email on phones.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_email_signature",
        "description": "Make a branded email signature that pastes cleanly into Gmail and Outlook: initials tile or "
                       "logo, name, job, business, tap-to-call phone, email, website and up to 4 social links, in "
                       "the brand colour with readable contrast. Saves signature.html and a plain-text copy in "
                       "Kinetic Web Designs/<business>/email, with paste-in steps. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "business": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "person": {"type": "string", "description": "The sender's name."},
                "role": {"type": "string", "description": "Their job, e.g. 'Owner'."},
                "phone": {"type": "string"},
                "email": {"type": "string"},
                "website": {"type": "string", "description": "e.g. lebosbakery.co.uk"},
                "logo_url": {"type": "string", "description": "Optional https:// link to the logo picture."},
                "socials": {"type": "object", "description": "Up to 4 of instagram, tiktok, facebook, linkedin, "
                                                             "x, youtube mapped to their links."},
                "note": {"type": "string", "description": "Optional small line, e.g. opening hours."},
                "initials": {"type": "string", "description": "1-2 letters instead of the business initials."},
            },
            "required": ["business", "colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
