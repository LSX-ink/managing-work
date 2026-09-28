"""Letters, a CV and invoices: filled-in Markdown documents with a PDF copy, popped up on the screen.

Letters go in Documents/Letters, the CV in Documents/CV (its sections are kept in cv.json so one can be changed
without retyping the rest), invoices in Documents/Invoices, numbered in order from invoices.json.
"""

import json
from datetime import date, timedelta
from pathlib import Path

import docs_tools as dt
import memory
import screen
from config import Settings

CV_SECTIONS = ["contact", "profile", "experience", "education", "skills", "interests", "references"]
SYMBOLS = {"GBP": "£", "EUR": "€", "USD": "$", "ZAR": "R"}
MAX_ITEMS = 100
MAX_FIELD = 4000


def uk_date(day: date) -> str:
    return f"{day.day} {day:%B %Y}"


def _text(args: dict, key: str) -> str:
    return str(args.get(key) or "").strip()[:MAX_FIELD]


def _lines(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).splitlines() if line.strip())


def pdf_card(settings: Settings, md: Path, said: str) -> screen.Shown:
    pdf = dt.export_pdf(settings, md)
    return screen.Shown(said, screen.file_card(settings, pdf, buttons=[
        {"label": "Show Markdown", "say": f"Show the document {md.stem}."}]))


# ---- Letter --------------------------------------------------------------------------------------

def letter(settings: Settings, args: dict, today: date | None = None) -> screen.Shown:
    body = _text(args, "body")
    if not body:
        raise ValueError("What should the letter say?")
    recipient = _lines(_text(args, "recipient"))
    subject = _text(args, "subject")
    greeting = _text(args, "greeting") or "Dear Sir or Madam,"
    sign_off = _text(args, "sign_off") or ("Yours sincerely," if not greeting.startswith("Dear Sir") else "Yours faithfully,")
    parts = [_lines(_text(args, "sender")), _text(args, "date") or uk_date(today or date.today()), recipient,
             f"**{subject}**" if subject else "", greeting, body, f"{sign_off}\n\n{_text(args, 'name')}".strip()]
    md = "\n\n".join(p for p in parts if p) + "\n"
    title = f"Letter - {subject or (recipient.splitlines()[0] if recipient else 'untitled')}"[:60]
    path = memory.unique_path(dt.home(settings, "Letters") / f"{memory.safe_name(title, 'title')}.md")
    dt.write(path, md)
    return pdf_card(settings, path, f"Wrote the letter as {path.stem}, with a PDF copy. It's on the screen.")


# ---- CV --------------------------------------------------------------------------------------------

def cv_path(settings: Settings) -> Path:
    return memory.root(settings) / "cv.json"


def cv_load(settings: Settings) -> dict:
    try:
        found = json.loads(cv_path(settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        found = {}
    return found if isinstance(found, dict) else {}


def cv_markdown(cv: dict) -> str:
    parts = [f"# {cv.get('name') or 'Curriculum Vitae'}"]
    if cv.get("contact"):
        parts.append(_lines(cv["contact"]))
    for section in CV_SECTIONS[1:]:
        if cv.get(section):
            parts.append(f"## {section.title()}\n\n{cv[section]}")
    return "\n\n".join(parts) + "\n"


def cv_render(settings: Settings, cv: dict, said: str) -> screen.Shown:
    title = memory.safe_name(f"{cv.get('name') or 'My'} CV", "title")
    path = dt.home(settings, "CV") / f"{title}.md"
    dt.write(path, cv_markdown(cv))
    return pdf_card(settings, path, said)


def cv_section(settings: Settings, args: dict) -> screen.Shown:
    cv = cv_load(settings)
    section = str(args.get("section") or "").strip().lower()
    if args.get("name"):
        cv["name"] = _text(args, "name")[:80]
    if section:
        if section not in CV_SECTIONS:
            raise ValueError(f"CV sections are {', '.join(CV_SECTIONS)}.")
        text = _text(args, "text")
        cv[section] = f"{cv[section].rstrip()}\n{text}" if args.get("append") and cv.get(section) else text
    elif not args.get("name"):
        raise ValueError("Which section of the CV?")
    cv_path(settings).write_text(json.dumps(cv, indent=2), encoding="utf-8")
    done = f"Updated the {section} section" if section else "Updated the name"
    return cv_render(settings, cv, f"{done} of your CV and made a fresh PDF. It's on the screen.")


def cv_show(settings: Settings, args: dict) -> screen.Shown | str:
    cv = cv_load(settings)
    if not any(cv.get(s) for s in CV_SECTIONS):
        return "Your CV is empty. Tell me your profile, experience, education and skills and I'll build it."
    missing = [s for s in ("profile", "experience", "education", "skills") if not cv.get(s)]
    tip = f" Still to fill in: {', '.join(missing)}." if missing else ""
    return cv_render(settings, cv, f"Here's your CV.{tip}")


# ---- Invoice ---------------------------------------------------------------------------------------

def invoices_path(settings: Settings) -> Path:
    return memory.root(settings) / "invoices.json"


def invoices_load(settings: Settings) -> dict:
    try:
        found = json.loads(invoices_path(settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        found = {}
    found = found if isinstance(found, dict) else {}
    return {"next": int(found.get("next") or 1), "issued": list(found.get("issued") or [])}


def money(settings: Settings, amount: float) -> str:
    code = settings.currency
    return f"{SYMBOLS[code]}{amount:,.2f}" if code in SYMBOLS else f"{amount:,.2f} {code}"


def _amount(value, what: str) -> float:
    try:
        n = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValueError(f"The {what} must be a number.") from None
    if not -10_000_000 < n < 10_000_000:
        raise ValueError(f"That {what} doesn't look right.")
    return n


def invoice(settings: Settings, args: dict, today: date | None = None) -> screen.Shown:
    client = _lines(_text(args, "recipient"))
    items = (args.get("items") or [])[:MAX_ITEMS]
    if not client or not items:
        raise ValueError("An invoice needs who it's to and at least one item.")
    today = today or date.today()
    lines, subtotal = [], 0.0
    for item in items:
        desc = str(item.get("description") or "").strip()[:200] or "Item"
        qty = _amount(item.get("quantity", 1), "quantity")
        price = _amount(item.get("price"), "price")
        cost = round(qty * price, 2)
        subtotal += cost
        q = f"{qty:g}"
        lines.append(f"- {desc}: {q} x {money(settings, price)} = **{money(settings, cost)}**")
    vat_rate = _amount(args.get("vat_rate", 20), "VAT rate") if args.get("vat") else 0.0
    vat = round(subtotal * vat_rate / 100, 2)
    total = round(subtotal + vat, 2)
    book = invoices_load(settings)
    number = f"INV-{book['next']:04d}"
    due = today + timedelta(days=int(args.get("due_days") or 30))
    totals = [f"Subtotal: {money(settings, subtotal)}"]
    if vat_rate:
        totals.append(f"VAT at {vat_rate:g}%: {money(settings, vat)}")
    totals.append(f"**Total due: {money(settings, total)}**")
    parts = [f"# Invoice {number}", _lines(_text(args, "sender")),
             f"Date: {uk_date(today)}\nPayment due: {uk_date(due)}", f"**Bill to:**\n{client}",
             "## Items", "\n".join(lines), "## Total", "\n".join(totals), _text(args, "notes")]
    md = "\n\n".join(p for p in parts if p) + "\n"
    name = memory.safe_name(f"{number} {client.splitlines()[0]}"[:60], "title")
    path = memory.unique_path(dt.home(settings, "Invoices") / f"{name}.md")
    dt.write(path, md)
    book["issued"].append({"number": number, "to": client.splitlines()[0], "date": today.isoformat(),
                           "due": due.isoformat(), "subtotal": round(subtotal, 2), "vat": vat, "total": total,
                           "file": dt.rel(settings, path)})
    book["next"] += 1
    invoices_path(settings).write_text(json.dumps(book, indent=2), encoding="utf-8")
    return pdf_card(settings, path, f"Invoice {number} for {money(settings, total)} is ready, with a PDF. It's on the screen.")


# ---- Tool ----------------------------------------------------------------------------------------

ACTIONS = ["letter", "cv_section", "cv_show", "invoice"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "document_forms",
        "description": "Make a formal letter, the user's CV or an invoice, saved as a document and a PDF and popped "
                       "up on the screen. action: 'letter' (you write the body); 'cv_section' sets or adds to one CV "
                       "section (contact, profile, experience, education, skills, interests, references) or the name; "
                       "'cv_show' builds and shows the CV; 'invoice' makes a numbered invoice from line items, with "
                       "VAT if asked.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "sender": {"type": "string", "description": "letter/invoice: sender's name and address, one per line."},
                "recipient": {"type": "string", "description": "letter/invoice: who it's to, name and address lines."},
                "date": {"type": "string", "description": "letter: date to print; default today."},
                "subject": {"type": "string"},
                "greeting": {"type": "string", "description": "letter: e.g. 'Dear Ms Smith,'."},
                "body": {"type": "string", "description": "letter: the letter's paragraphs."},
                "sign_off": {"type": "string", "description": "letter: e.g. 'Yours sincerely,'."},
                "name": {"type": "string", "description": "letter: signature name; cv_section: the CV's name."},
                "section": {"type": "string", "enum": CV_SECTIONS},
                "text": {"type": "string", "description": "cv_section: the section in Markdown (lists welcome)."},
                "append": {"type": "boolean", "description": "cv_section: add to the section instead of replacing it."},
                "items": {"type": "array", "items": {"type": "object", "properties": {
                    "description": {"type": "string"}, "quantity": {"type": "number"}, "price": {"type": "number"}},
                    "required": ["description", "price"], "additionalProperties": False}},
                "vat": {"type": "boolean", "description": "invoice: add VAT."},
                "vat_rate": {"type": "number", "description": "invoice: VAT percent, default 20."},
                "due_days": {"type": "integer", "description": "invoice: days to pay, default 30."},
                "notes": {"type": "string", "description": "invoice: e.g. bank details or thanks."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"document_forms"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "letter":
        return letter(settings, args)
    if action == "cv_section":
        return cv_section(settings, args)
    if action == "cv_show":
        return cv_show(settings, args)
    if action == "invoice":
        return invoice(settings, args)
    raise ValueError(f"Pick an action: {', '.join(ACTIONS)}.")
