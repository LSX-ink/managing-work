"""Kinetic Web Designs invoices: numbered, printable invoices (from a quote's deposit or final balance, or your own
items), what's paid, unpaid and overdue, polite payment reminders and what the business has earned.

Invoices are saved as HTML pages in Kinetic Web Designs/Clients/<client> (open one and print it to PDF to send it), with
your bank details from web_design_sales my_details so the client pays you directly. The list is kinetic-invoices.json.
Alfred never sends an invoice or reminder and never takes or moves money: he only marks an invoice paid when you say
the money has arrived.
"""

from datetime import date, timedelta
from html import escape

import kinetic_sales
import kinetic_store as st
import screen
from config import Settings

NAMES = {"web_design_invoices"}
ACTIONS = ["invoice", "invoices", "paid", "reminder", "earnings", "cancel"]
PARTS = ["deposit", "final", "full"]
DEFAULT_DUE_DAYS = 14


def find_invoice(rows: list[dict], which) -> dict:
    key = str(which or "").strip().upper()
    if not key:
        raise ValueError("Which invoice? Give its number, e.g. INV-0001, or the client.")
    if key.isdigit():
        key = f"INV-{int(key):04d}"
    hit = next((r for r in rows if r["number"] == key), None)
    if not hit:
        hits = [r for r in rows if key.lower() in r["client"].lower() and r["status"] == "unpaid"] or \
            [r for r in rows if key.lower() in r["client"].lower()]
        hit = hits[-1] if hits else None
    if not hit:
        raise ValueError("I can't find that invoice.")
    return hit


def state(inv: dict, today: date) -> str:
    if inv["status"] != "unpaid":
        return inv["status"]
    late = (today - date.fromisoformat(inv["due"])).days
    return f"overdue {late} day{'s' if late != 1 else ''}" if late > 0 else "unpaid"


def lines_for(settings: Settings, args: dict) -> tuple[str, list[tuple[str, int, float]], str]:
    """(client, [(description, qty, unit price)], quote number or '')."""
    if args.get("quote"):
        rows = st.rows_of(settings, st.QUOTES)
        q = kinetic_sales.find_quote(rows, args["quote"])
        part = args.get("part") or "deposit"
        if part not in PARTS:
            raise ValueError("Which part of the quote? deposit, final or full.")
        already = sum(i["total"] for i in st.rows_of(settings, st.INVOICES)
                      if i.get("quote") == q["number"] and i["status"] != "cancelled")
        if part == "deposit":
            if not q["deposit"]:
                raise ValueError(f"Quote {q['number']} has no deposit; make the full invoice instead.")
            amount, what = q["deposit"], "Deposit"
        elif part == "final":
            amount, what = round(q["total"] - already, 2), "Final balance"
        else:
            amount, what = round(q["total"] - already, 2), "Website"
        if amount <= 0:
            raise ValueError(f"Quote {q['number']} has already been invoiced in full.")
        package = kinetic_sales.prices(settings)["packages"][q["package"]]["name"]
        lines = [(f"{what} for {package.lower()} (quote {q['number']})", 1, amount)]
        if q["status"] in ("draft", "sent"):
            q["status"] = "accepted"
            st.save(settings, st.QUOTES, rows)
        return q["client"], lines, q["number"]
    client = st.need(args.get("client"), "client", 80)
    lines = []
    for item in args.get("items") or []:
        if isinstance(item, dict) and st.clean(item.get("description")):
            qty = int(item.get("qty") or 1)
            if not 1 <= qty <= 1000:
                raise ValueError("That quantity doesn't look right.")
            lines.append((st.clean(item["description"], 160), qty, st.number(item.get("price"), "item price")))
    if not lines:
        raise ValueError("What's the invoice for? Give a quote number, or items with prices.")
    return client, lines, ""


def invoice(settings: Settings, args: dict) -> screen.Shown:
    client, lines, quote_no = lines_for(settings, args)
    rows = st.rows_of(settings, st.INVOICES)
    if len(rows) >= st.MAX_ROWS:
        raise ValueError("The invoice list is full.")
    iid = st.next_id(rows)
    number = f"INV-{iid:04d}"
    issued = st.today()
    due = issued + timedelta(days=int(st.number(args.get("due_days") or DEFAULT_DUE_DAYS, "number of days", False, 120)))
    total = round(sum(q * u for _, q, u in lines), 2)
    me = st.business(settings)
    meta = [("Invoice number", number), ("Date", st.short(issued)), ("Due", st.long_date(due)), ("Bill to", client)]
    if quote_no:
        meta.append(("Quote", quote_no))
    table = ["<table><tr><th>Description</th><th class=n>Qty</th><th class=n>Price</th><th class=n>Amount</th></tr>"]
    table += [f"<tr><td>{escape(d)}</td><td class=n>{q}</td><td class=n>{st.gbp(u)}</td><td class=n>{st.gbp(q * u)}</td></tr>"
              for d, q, u in lines]
    table.append(f"<tr class=total><td>Amount due</td><td></td><td></td><td class=n>{st.gbp(total)}</td></tr></table>")
    if me["sort_code"] and me["account_number"]:
        pay = (f"<div class=note><b>Pay by bank transfer</b><br>Account name: {escape(me['bank_name'] or me['owner'] or me['name'])}"
               f"<br>Sort code: {escape(me['sort_code'])}<br>Account number: {escape(me['account_number'])}"
               f"<br>Reference: {number}</div>")
    else:
        pay = f"<div class=note><b>Pay by bank transfer</b><br>[Add your bank details]<br>Reference: {number}</div>"
    vat = f"<p>VAT number: {escape(me['vat_number'])}</p>" if me["vat_number"] else "<p>No VAT is charged.</p>"
    body = [f"<h2>Invoice {number}</h2>",
            '<div class="meta">' + "".join(f"<div><b>{k}</b>{escape(v)}</div>" for k, v in meta) + "</div>",
            "".join(table), pay, vat,
            f"<footer>Payment is due by {st.long_date(due)}. Thank you for your business.</footer>"]
    path = st.write(settings, ("Clients", client), f"Invoice {number}.html",
                    st.doc_html(settings, f"Invoice {number} for {client}", "\n".join(body)))
    rows.append({"id": iid, "number": number, "client": client, "quote": quote_no, "total": total,
                 "issued": issued.isoformat(), "due": due.isoformat(), "status": "unpaid", "paid_on": "",
                 "lines": [[d, q, u] for d, q, u in lines], "file": st.where(settings, path)})
    st.save(settings, st.INVOICES, rows)
    text = f"Invoice {number} for {client}: {st.gbp(total)}, due {st.long_date(due)}. Saved in {st.where(settings, path)}; " \
           f"open it and print to PDF to send it. {st.NOT_SENT}"
    if not (me["sort_code"] and me["account_number"]):
        text += " Your bank details aren't saved yet, so add them with 'set my bank details' and make it again, or " \
                "fill them in before sending."
    return st.file_shown(settings, path, text, [{"label": "Mark paid", "say": f"Invoice {number} has been paid."}])


def invoices(settings: Settings, args: dict) -> screen.Shown:
    rows = st.rows_of(settings, st.INVOICES)
    if not rows:
        raise ValueError("No invoices yet. Ask me to make one from a quote.")
    today = st.today()
    unpaid = [r for r in rows if r["status"] == "unpaid"]
    late = [r for r in unpaid if state(r, today).startswith("overdue")]
    if args.get("client"):
        rows = [r for r in rows if str(args["client"]).lower() in r["client"].lower()]
    text = f"{len(unpaid)} unpaid invoice{'s' if len(unpaid) != 1 else ''} worth {st.gbp(sum(r['total'] for r in unpaid))}"
    text += f", {len(late)} overdue ({st.gbp(sum(r['total'] for r in late))})." if late else "; none overdue."
    table = [[r["number"], r["client"], st.gbp(r["total"]), r["due"], state(r, today)] for r in rows[::-1][:60]]
    buttons = [{"label": f"Chase {late[0]['number']}", "say": f"Draft a payment reminder for {late[0]['number']}."}] if late else []
    return st.table(text, "Invoices", ["Invoice", "Client", "Amount", "Due", "Status"], table, buttons)


def paid(settings: Settings, args: dict) -> str:
    rows = st.rows_of(settings, st.INVOICES)
    inv = find_invoice(rows, args.get("invoice"))
    if inv["status"] == "paid":
        return f"{inv['number']} was already marked paid on {inv['paid_on']}."
    when = st.parse_date(args.get("date"), "payment date") or st.today()
    inv.update(status="paid", paid_on=when.isoformat())
    st.save(settings, st.INVOICES, rows)
    left = [r for r in rows if r.get("quote") and r.get("quote") == inv.get("quote") and r["status"] == "unpaid"]
    out = f"Marked {inv['number']} from {inv['client']} as paid: {st.gbp(inv['total'])}."
    if inv.get("quote") and not left:
        quotes = st.rows_of(settings, st.QUOTES)
        q = next((x for x in quotes if x["number"] == inv["quote"]), None)
        billed = sum(r["total"] for r in rows if r.get("quote") == inv["quote"] and r["status"] != "cancelled")
        if q and billed < q["total"]:
            out += f" When the site is finished, say \"make the final invoice for {q['number']}\" for the other {st.gbp(q['total'] - billed)}."
    return out


def reminder(settings: Settings, args: dict) -> screen.Shown:
    rows = st.rows_of(settings, st.INVOICES)
    inv = find_invoice(rows, args.get("invoice"))
    if inv["status"] != "unpaid":
        raise ValueError(f"{inv['number']} is {inv['status']}, so there's nothing to chase.")
    me = st.business(settings)
    days = (st.today() - date.fromisoformat(inv["due"])).days
    sign = me["owner"] or "[your name]"
    hello = f"Hi {st.clean(args.get('contact_name'), 40)}," if args.get("contact_name") else "Hi,"
    if days <= 0:
        line = f"Just a friendly reminder that invoice {inv['number']} for {st.gbp(inv['total'])} is due on {st.long_date(date.fromisoformat(inv['due']))}."
    elif days <= 14:
        line = (f"I hope all's well. Invoice {inv['number']} for {st.gbp(inv['total'])} was due on "
                f"{st.long_date(date.fromisoformat(inv['due']))} and I haven't received it yet. Could you let me know "
                "when it'll be paid? It may simply have been missed.")
    else:
        line = (f"Invoice {inv['number']} for {st.gbp(inv['total'])} is now {days} days overdue. Please pay it within "
                "7 days. Under the Late Payment of Commercial Debts Act I'm entitled to add interest and a fixed "
                "charge to business invoices paid late, which I'd rather not do.")
    bank = f"\n\nBank: sort code {me['sort_code']}, account {me['account_number']}, reference {inv['number']}." \
        if me["sort_code"] and me["account_number"] else ""
    body = (f"Subject: Invoice {inv['number']} from {me['name']}\n\n{hello}\n\n{line}{bank}\n\nI've attached a copy "
            f"of the invoice. If you've already paid, thank you, and please ignore this.\n\nThanks,\n{sign}\n{me['name']}")
    path = st.write(settings, ("Clients", inv["client"]), f"Reminder {inv['number']} {st.today().isoformat()}.md", body + "\n")
    tone = "a friendly" if days <= 14 else "a firmer"
    return st.text_card(f"I drafted {tone} reminder for {inv['number']} ({inv['client']}) and saved it in "
                        f"{st.where(settings, path)}. {st.NOT_SENT}" +
                        (" For late payment interest, ask the freelance money tool to work it out." if days > 14 else ""),
                        f"Reminder: {inv['number']}", body)


def earnings(settings: Settings, args: dict) -> screen.Shown:
    rows = [r for r in st.rows_of(settings, st.INVOICES) if r["status"] != "cancelled"]
    today = st.today()
    paid_rows = [r for r in rows if r["status"] == "paid" and r.get("paid_on")]
    month = sum(r["total"] for r in paid_rows if r["paid_on"][:7] == today.isoformat()[:7])
    year = sum(r["total"] for r in paid_rows if r["paid_on"][:4] == str(today.year))
    owed = sum(r["total"] for r in rows if r["status"] == "unpaid")
    quotes = st.rows_of(settings, st.QUOTES)
    pipeline = sum(q["total"] for q in quotes if q["status"] in ("draft", "sent"))
    care = sum(q.get("care", 0) for q in quotes if q["status"] == "accepted")
    text = (f"Kinetic Web Designs has been paid {st.gbp(month)} this month and {st.gbp(year)} this year. "
            f"{st.gbp(owed)} is owed to you and {st.gbp(pipeline)} is in open quotes.")
    if care:
        text += f" Accepted care plans could bring in up to {st.gbp(care)} a month."
    rows_ = [["Paid this month", st.gbp(month)], ["Paid this year", st.gbp(year)], ["Owed to you", st.gbp(owed)],
             ["In open quotes", st.gbp(pipeline)], ["Care plans (monthly, if taken)", st.gbp(care)]]
    return st.table(text + " Remember to keep some aside for tax; GOV.UK has the current rules.",
                    "Kinetic Web Designs money", ["", "Amount"], rows_)


def cancel(settings: Settings, args: dict) -> str:
    rows = st.rows_of(settings, st.INVOICES)
    inv = find_invoice(rows, args.get("invoice"))
    if not args.get("confirmed"):
        return f"Should I cancel {inv['number']} for {inv['client']} ({st.gbp(inv['total'])})? Say yes to confirm."
    inv["status"] = "cancelled"
    st.save(settings, st.INVOICES, rows)
    return f"Cancelled {inv['number']}. The file stays in the client's folder, marked cancelled in your list."


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_design_invoices",
        "description": "Kinetic Web Designs invoices. invoice: a numbered printable invoice from a quote (part: "
                       "deposit, final or full) or from items, with the user's bank details. invoices: paid, unpaid "
                       "and overdue. paid: mark an invoice paid, only when the user says the money arrived. reminder: "
                       "a payment reminder draft (friendly, then firmer when over 14 days late). earnings: paid this "
                       "month and year, owed, open quotes. cancel needs confirmed true after the user says yes. Never "
                       "send anything or take payment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "quote": {"type": "string", "description": "invoice: quote number like Q-0001."},
                "part": {"type": "string", "enum": PARTS, "description": "invoice from a quote: default deposit."},
                "client": {"type": "string"},
                "items": {"type": "array", "items": {"type": "object", "properties": {
                    "description": {"type": "string"}, "qty": {"type": "integer"}, "price": {"type": "number"}}}},
                "due_days": {"type": "integer", "description": f"Days to pay (default {DEFAULT_DUE_DAYS})."},
                "invoice": {"type": "string", "description": "Invoice number like INV-0001, or the client."},
                "date": {"type": "string", "description": "paid: YYYY-MM-DD, today or yesterday."},
                "contact_name": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"invoice": invoice, "invoices": invoices, "paid": paid, "reminder": reminder, "earnings": earnings,
                "cancel": cancel}
    return st.dispatch(handlers, args.get("action"), settings, args, "invoice")
