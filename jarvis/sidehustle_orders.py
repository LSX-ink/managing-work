"""Side-hustle customers and orders: a simple order log with statuses, customers with repeat counts and notes. Marking an
order paid also logs the income (sidehustle-log.json) once. Data: sidehustle-orders.json, sidehustle-customers.json."""

import screen
import sidehustle_store as st
from config import Settings

STATUSES = ["enquiry", "agreed", "in progress", "delivered", "paid", "cancelled"]
MAX_ORDERS = 1000


def _orders(settings: Settings) -> list[dict]:
    return [o for o in st.load(settings, st.ORDERS, []) if isinstance(o, dict)]


def _money(o: dict) -> str:
    return st.gbp(o["price"])


def order_add(settings: Settings, args: dict) -> screen.Shown:
    rows = _orders(settings)
    if len(rows) >= MAX_ORDERS:
        raise ValueError("The order log is full.")
    status = args.get("status") or "enquiry"
    if status not in STATUSES:
        raise ValueError("An order's status is one of " + ", ".join(STATUSES) + ".")
    due = st.parse_date(args.get("due"), "due date")
    order = {"id": max([o["id"] for o in rows] + [0]) + 1, "hustle": st.hustle_name(settings, args.get("hustle")),
             "customer": st.need(args.get("customer"), "customer", 60), "item": st.need(args.get("item"), "item", 80),
             "price": st.number(args.get("price"), "price", allow_zero=True), "status": "enquiry",
             "date": st.today().isoformat(), "due": due.isoformat() if due else "", "note": st.clean(args.get("note"), 120),
             "logged": False}
    rows.append(order)
    st.save(settings, st.ORDERS, rows)
    if status != "enquiry":
        return order_update(settings, {"order_id": order["id"], "status": status})
    return _table(rows, f"Added order {order['id']} for {order['customer']}.")


def _find(rows: list[dict], args: dict) -> dict:
    if args.get("order_id") is not None:
        hit = next((o for o in rows if o["id"] == int(args["order_id"])), None)
    else:
        name = st.need(args.get("customer"), "order number or customer").lower()
        hits = [o for o in rows if name in o["customer"].lower() and o["status"] not in ("paid", "cancelled")]
        if len(hits) > 1:
            raise ValueError(f"{len(hits)} open orders for {args['customer']}; give the order number.")
        hit = hits[0] if hits else None
    if not hit:
        raise ValueError("I can't find that order.")
    return hit


def order_update(settings: Settings, args: dict) -> screen.Shown:
    rows = _orders(settings)
    o = _find(rows, args)
    if args.get("status"):
        if args["status"] not in STATUSES:
            raise ValueError("An order's status is one of " + ", ".join(STATUSES) + ".")
        o["status"] = args["status"]
    if args.get("price") is not None:
        o["price"] = st.number(args["price"], "price", allow_zero=True)
    if args.get("due"):
        o["due"] = st.parse_date(args["due"], "due date").isoformat()
    if args.get("note"):
        o["note"] = st.clean(args["note"], 120)
    extra = ""
    if o["status"] == "paid" and not o["logged"] and o["price"] > 0:
        st.add_entry(settings, "income", o["hustle"], o["price"], f"order {o['id']}: {o['item']}", customer=o["customer"])
        o["logged"] = True
        extra = f" Logged {_money(o)} income."
    st.save(settings, st.ORDERS, rows)
    return _table(rows, f"Order {o['id']} is now {o['status']}.{extra}")


def _table(rows: list[dict], prefix: str = "", shown: list[dict] | None = None) -> screen.Shown:
    shown = rows if shown is None else shown
    if not shown:
        raise ValueError("No orders to show.")
    unpaid = sum(o["price"] for o in rows if o["status"] == "delivered")
    open_n = sum(1 for o in rows if o["status"] not in ("paid", "cancelled"))
    text = f"{prefix} {open_n} open, {st.gbp(unpaid)} delivered and waiting to be paid.".strip()
    table = [[str(o["id"]), o["customer"], o["item"], _money(o), o["status"], o["due"] or "-"] for o in shown[::-1][:30]]
    return screen.Shown(text, screen.card("table", "Side hustle orders", "sidehustle-orders",
                                          columns=["#", "Customer", "Item", "Price", "Status", "Due"], rows=table,
                                          buttons=[{"label": "Customers", "say": "Show my side hustle customers."}]))


def orders(settings: Settings, args: dict) -> screen.Shown:
    rows = _orders(settings)
    shown = rows
    if args.get("status"):
        shown = [o for o in shown if o["status"] == args["status"]]
    if args.get("hustle"):
        shown = [o for o in shown if args["hustle"].lower() in o["hustle"].lower()]
    if not rows:
        raise ValueError("No orders yet. Tell me about a customer and what they want.")
    return _table(rows, "", shown)


def customers(settings: Settings, args: dict) -> screen.Shown:
    groups: dict[str, list[dict]] = {}
    for o in _orders(settings):
        groups.setdefault(o["customer"].lower(), []).append(o)
    if not groups:
        raise ValueError("No customers yet.")
    notes = st.load(settings, st.CUSTOMERS, {})
    table = []
    for key, rows in sorted(groups.items(), key=lambda kv: -sum(o["price"] for o in kv[1] if o["status"] == "paid")):
        real = [o for o in rows if o["status"] != "cancelled"]
        paid = sum(o["price"] for o in real if o["status"] == "paid")
        table.append([rows[0]["customer"] + (" (repeat)" if len(real) > 1 else ""), str(len(real)), st.gbp(paid),
                      max(o["date"] for o in rows), notes.get(key, "")])
    return screen.Shown(f"You have {len(table)} customer{'s' if len(table) != 1 else ''}.", screen.card(
        "table", "Side hustle customers", "sidehustle-customers", columns=["Customer", "Orders", "Paid", "Last order", "Note"], rows=table))


def customer_note(settings: Settings, args: dict) -> str:
    name = st.need(args.get("customer"), "customer", 60)
    notes = st.load(settings, st.CUSTOMERS, {})
    notes[name.lower()] = st.need(args.get("note"), "note", 200)
    st.save(settings, st.CUSTOMERS, notes)
    return f"Noted for {name}."


def order_remove(settings: Settings, args: dict) -> str:
    rows = _orders(settings)
    o = _find(rows, args)
    if not args.get("confirmed"):
        return f"Remove order {o['id']} ({o['customer']}, {o['item']})? Say yes to confirm. Any income already logged stays."
    rows.remove(o)
    st.save(settings, st.ORDERS, rows)
    return f"Removed order {o['id']}."
