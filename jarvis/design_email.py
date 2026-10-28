"""Branded emails: an HTML email in the brand colour that looks right in Gmail, Outlook and Apple Mail.

make_email_template writes the email the way email apps need it, not like a web page: a 600px table layout with the
styles written on each tag, a hidden preview line (the grey text next to the subject in the inbox), the initials tile
or logo, a heading, the message, a "bulletproof" button that still shows when pictures are blocked, and a footer with
the business address and an unsubscribe line. Colours are checked so the button and every line of text pass WCAG AA,
with a dark-mode version for apps that support it. A plain-text copy is saved alongside, because good emails send
both. Files go in Kinetic Web Designs/<name>/email, ready for a client's welcome, booking or offer emails.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, UI, colour, fix, ratio
from design_extract import FOLDER
from design_logo import initials
from design_palette import on, scale

NAMES = {"make_email_template"}
WIDTH = 600
FONT = "-apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
PAGE, CARD, INK, MUTED = "#f4f4f5", "#ffffff", "#18181b", "#52525b"
CLIP = 102 * 1024  # Gmail cuts emails off ("[Message clipped]") past about 102KB
SUBJECT_MAX, PREHEADER_MIN, PREHEADER_MAX = 60, 40, 130


def link(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        return ""
    if re.match(r"(?i)^(mailto:|tel:)\S+$", url):
        return url
    if re.match(r"(?i)^https://[^\s/]+\.[^\s/]+(/\S*)?$", url):
        return url
    if re.match(r"(?i)^[\w-]+(\.[\w-]+)+(/\S*)?$", url):
        return "https://" + url
    raise ValueError("Use a full https:// link (or mailto: / tel:) for the button and logo.")


def paragraphs(text: str, style: str) -> str:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", str(text or "").replace("\r\n", "\n")) if b.strip()]
    return "".join(f'<p style="{style}">' + "<br>".join(html.escape(line.strip()) for line in b.split("\n")) + "</p>"
                   for b in blocks)


def colours(brand: str) -> dict[str, str]:
    """Button colour that stands out on white (3:1) with text that reads on it (4.5:1), plus dark-mode shades."""
    button = brand if ratio(brand, CARD) >= UI else fix(brand, CARD, UI)
    label = on(button)
    if ratio(label, button) < AA:  # a mid colour neither white nor black reads on: deepen it until white does
        button, label = fix(button, "#ffffff", AA), "#ffffff"
    shades = scale(brand)
    return {"brand": brand, "button": button, "label": label, "tile": button, "tile_text": label,
            "link": fix(button, CARD, AA), "dark_link": fix(shades[300], "#18181b", AA)}


def build(name: str, brand: str, subject: str, heading: str, message: str, preheader: str, button: str, url: str,
          footer: str, logo: str, mark: str) -> str:
    c = colours(brand)
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    text_style = f"margin:0 0 16px;font-family:{FONT};font-size:16px;line-height:1.6;color:{INK};"
    if logo:
        top = (f'<img src="{e(logo)}" width="120" alt="{e(name)}" style="display:block;border:0;outline:none;'
               f'max-width:120px;height:auto;">')
    else:
        top = (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td width="48" height="48" '
               f'align="center" valign="middle" bgcolor="{c["tile"]}" style="width:48px;height:48px;border-radius:12px;'
               f'background:{c["tile"]};font-family:{FONT};font-size:20px;font-weight:700;color:{c["tile_text"]};">'
               f'{e(mark)}</td><td style="padding-left:12px;font-family:{FONT};font-size:18px;font-weight:700;'
               f'color:{INK};" class="ink">{e(name)}</td></tr></table>')
    cta = ""
    if button and url:
        cta = (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 0;">'
               f'<tr><td align="center" bgcolor="{c["button"]}" style="border-radius:8px;background:{c["button"]};">'
               f'<a class="button" href="{e(url)}" target="_blank" style="display:inline-block;padding:14px 28px;'
               f'font-family:{FONT};font-size:16px;font-weight:700;line-height:1.2;color:{c["label"]};'
               f'text-decoration:none;border-radius:8px;">{e(button)}</a></td></tr></table>')
    foot = paragraphs(footer, f"margin:0 0 8px;font-family:{FONT};font-size:13px;line-height:1.5;color:{MUTED};")
    hidden = e(preheader) + "&#847;&zwnj;&nbsp;" * 30 if preheader else ""
    return f"""<!doctype html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting"><meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark"><title>{e(subject)}</title>
<style>
a {{ color: {c["link"]}; }}
@media (max-width: 620px) {{ .card {{ padding: 24px !important; }} .h1 {{ font-size: 24px !important; }} }}
@media (prefers-color-scheme: dark) {{
  .page {{ background: #09090b !important; }} .card {{ background: #18181b !important; }}
  .ink, .card p, .h1 {{ color: #f4f4f5 !important; }} .muted p {{ color: #a1a1aa !important; }}
  .card a:not(.button) {{ color: {c["dark_link"]} !important; }}
}}
</style></head>
<body style="margin:0;padding:0;background:{PAGE};" class="page">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{hidden}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{PAGE}" class="page"
style="background:{PAGE};"><tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="{WIDTH}" cellpadding="0" cellspacing="0" border="0"
style="width:100%;max-width:{WIDTH}px;">
<tr><td style="padding:0 0 20px;">{top}</td></tr>
<tr><td class="card" bgcolor="{CARD}"
style="background:{CARD};border-radius:16px;padding:40px;border-top:4px solid {c["brand"]};">
<h1 class="h1" style="margin:0 0 16px;font-family:{FONT};font-size:28px;line-height:1.25;font-weight:700;color:{INK};">
{e(heading)}</h1>
{paragraphs(message, text_style)}
{cta}
</td></tr>
<tr><td class="muted" style="padding:24px 8px 0;">{foot}</td></tr>
</table></td></tr></table>
</body></html>
"""


def plain(name: str, subject: str, heading: str, message: str, button: str, url: str, footer: str) -> str:
    parts = [f"Subject: {subject}", "", heading, "", str(message or "").strip()]
    if button and url:
        parts += ["", f"{button}: {url}"]
    parts += ["", "--", name] + ([str(footer).strip()] if footer else [])
    return "\n".join(parts).replace("\r\n", "\n") + "\n"


def run(settings: Settings, args: dict) -> str:
    name = " ".join(str(args.get("name") or "").split())
    if not name:
        raise ValueError("Give the brand or client a name for the email.")
    brand = colour(args.get("colour") or "")
    heading = " ".join(str(args.get("heading") or f"Hello from {name}").split())
    subject = " ".join(str(args.get("subject") or heading).split())
    message = str(args.get("message") or "").strip()
    if not message:
        raise ValueError("Say what the email should say (the message).")
    preheader = " ".join(str(args.get("preheader") or "").split())
    button = " ".join(str(args.get("button_text") or "").split())
    url = link(args.get("button_url") or "")
    logo = link(args.get("logo_url") or "")
    if logo.startswith(("mailto:", "tel:")):
        raise ValueError("The logo needs an https:// picture link.")
    footer = str(args.get("footer") or f"You're getting this because you're a customer of {name}.\n"
                                        "Reply STOP or use the unsubscribe link to stop these emails.")
    template = memory.safe_name(str(args.get("template") or "email"), "email name").lower().replace(" ", "-")
    page = build(name, brand, subject, heading, message, preheader, button, url, footer, logo,
                 initials(name, str(args.get("initials") or "")))
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/email", create=True)
    (path / f"{template}.html").write_text(page, encoding="utf-8")
    (path / f"{template}.txt").write_text(plain(name, subject, heading, message, button, url, footer), encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    c = colours(brand)
    notes = []
    if c["button"] != brand:
        notes.append(f"the brand colour is too light for a button on white, so the button uses {c['button']}")
    if button and not url:
        notes.append("the button was left out because it has no link")
    if len(subject) > SUBJECT_MAX:
        notes.append(f"the subject is {len(subject)} letters; phones show about {SUBJECT_MAX}")
    if not preheader:
        notes.append("add a preheader (the preview line next to the subject) so the inbox shows more than the "
                     "first words")
    elif not PREHEADER_MIN <= len(preheader) <= PREHEADER_MAX:
        notes.append(f"the preheader is {len(preheader)} letters; {PREHEADER_MIN}-{PREHEADER_MAX} shows best")
    size = len(page.encode("utf-8"))
    if size > CLIP:
        notes.append(f"it's {size // 1024}KB, so Gmail will clip it; shorten the message")
    return (f"Made {template}.html and {template}.txt for {name} in {where}: a 600px email in the brand colour with "
            f"{'the logo' if logo else 'the initials tile'}, the heading, the message"
            f"{', a ' + repr(button) + ' button' if button and url else ''} and a footer, plus a dark-mode version. "
            f"Paste the HTML into the email app or service (e.g. Resend or Mailchimp) and send the .txt as the plain "
            f"version." + (" Heads up: " + "; ".join(notes) + "." if notes else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_email_template",
        "description": "Make a branded HTML email that works in Gmail, Outlook and Apple Mail: 600px table layout with "
                       "inline styles, a hidden preview line, initials tile or logo, heading, message, a button that "
                       "shows even with pictures off, footer with unsubscribe line, dark mode and colours checked for "
                       "WCAG AA. Saves <template>.html and a plain-text <template>.txt in Kinetic Web "
                       "Designs/<name>/email. Use for a client's welcome, booking, offer or newsletter emails. Answer "
                       "in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Brand or client name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "template": {"type": "string", "description": "Which email, e.g. 'welcome' or 'booking' (the file "
                                                              "name)."},
                "subject": {"type": "string", "description": "Subject line, under 60 letters."},
                "preheader": {"type": "string", "description": "Preview line shown after the subject (40-130 "
                                                              "letters)."},
                "heading": {"type": "string", "description": "Big heading at the top of the email."},
                "message": {"type": "string", "description": "The email's words; a blank line starts a new "
                                                            "paragraph."},
                "button_text": {"type": "string", "description": "Button words, e.g. 'Book your table'."},
                "button_url": {"type": "string", "description": "https:// link (or mailto:/tel:) for the button."},
                "logo_url": {"type": "string", "description": "Optional https:// link to the logo picture."},
                "footer": {"type": "string", "description": "Footer: business name, address, unsubscribe words."},
                "initials": {"type": "string", "description": "1-2 letters instead of the name's initials."},
            },
            "required": ["name", "colour", "message"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
