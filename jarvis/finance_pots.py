"""Savings pots, cash envelopes, net worth snapshots and a receipt log.

Pots have a target and remember every deposit and withdrawal (for the monthly report and tax year).
Envelopes are the cash envelope system: a set amount each, spent down. Net worth is dated snapshots of
assets and liabilities. Receipts can point at a photo of the receipt in a memory folder.
Each is a finance-*.json file in the memory folder; amounts are in the user's currency.
"""

import finance_store as fs
import homestore as hs
import screen
from config import Settings

MAX_HISTORY = 500


# Savings pots

def pot_create(settings: Settings, name, target) -> str:
    name = hs.need(name, "pot", 40)
    pots = fs.rows(settings, fs.POTS)
    key = hs.find(pots, name) or name
    pot = pots.get(key) or {"saved": 0.0, "history": []}
    pot["target"] = fs.amount(target, "target")
    fs.put(settings, fs.POTS, pots, key, pot)
    return f"The {key} pot has a target of {fs.cash(pot['target'], settings)}; {fs.cash(pot['saved'], settings)} saved so far."


def pot_move(settings: Settings, name, value, sign: int) -> screen.Shown:
    pots = fs.rows(settings, fs.POTS)
    key = fs.key_of(pots, name, "savings pot")
    pot, number = pots[key], fs.amount(value)
    if sign < 0 and number > pot.get("saved", 0) + 0.001:
        raise ValueError(f"The {key} pot only has {fs.cash(pot.get('saved', 0), settings)} in it.")
    pot["saved"] = round(pot.get("saved", 0) + sign * number, 2)
    pot["history"] = (list(pot.get("history") or []) + [{"date": hs.today().isoformat(), "amount": sign * number}])[-MAX_HISTORY:]
    fs.put(settings, fs.POTS, pots, key, pot)
    verb = "Added" if sign > 0 else "Took"
    said = f"{verb} {fs.cash(number, settings)} {'to' if sign > 0 else 'from'} {key}. " + _pot_progress(settings, key, pot)
    return pots_show(settings, said)


def _pot_progress(settings: Settings, key: str, pot: dict) -> str:
    target, saved = pot.get("target", 0), pot.get("saved", 0)
    if target and saved >= target:
        return f"That's the {fs.cash(target, settings)} target reached."
    pct = f", {saved / target:.0%} of the target" if target else ""
    return f"It has {fs.cash(saved, settings)}{pct}."


def pots_show(settings: Settings, said: str = "") -> screen.Shown | str:
    pots = fs.rows(settings, fs.POTS)
    if not pots:
        return "No savings pots yet. Say something like 'make a holiday pot with a target of 1,500'."
    rows = [fs.meter(k, p.get("saved", 0), p.get("target", 0) or p.get("saved", 0) or 1, settings,
                     say=f"How's my {k} pot doing?") for k, p in sorted(pots.items())]
    total = sum(p.get("saved", 0) for p in pots.values())
    said = said or f"{hs.plural(len(pots), 'pot')} with {fs.cash(total, settings)} saved in total."
    return fs.board(said, "Savings pots", "finance-pots", [fs.section("meters", "Saved vs target", rows=rows)])


def pot_remove(settings: Settings, name, confirmed: bool) -> str:
    pots = fs.rows(settings, fs.POTS)
    key = fs.key_of(pots, name, "savings pot")
    if not confirmed:
        return f"Ask the user to confirm deleting the {key} pot and its history, then call again with confirmed true."
    del pots[key]
    hs.save(settings, fs.POTS, pots)
    return f"Deleted the {key} pot."


# Cash envelopes

def envelope_set(settings: Settings, name, value) -> str:
    name = hs.need(name, "envelope", 40)
    found = fs.rows(settings, fs.ENVELOPES)
    key = hs.find(found, name) or name
    number = fs.amount(value)
    fs.put(settings, fs.ENVELOPES, found, key, {"amount": number, "left": number, "spends": []})
    return f"The {key} envelope has {fs.cash(number, settings)}."


def envelope_spend(settings: Settings, name, value, what) -> screen.Shown:
    found = fs.rows(settings, fs.ENVELOPES)
    key = fs.key_of(found, name, "envelope")
    env, number = found[key], fs.amount(value)
    if number > env.get("left", 0) + 0.001:
        raise ValueError(f"The {key} envelope only has {fs.cash(env.get('left', 0), settings)} left.")
    env["left"] = round(env.get("left", 0) - number, 2)
    env["spends"] = (list(env.get("spends") or []) + [{"date": hs.today().isoformat(), "amount": number,
                                                        "what": hs.clean(what, 60)}])[-MAX_HISTORY:]
    fs.put(settings, fs.ENVELOPES, found, key, env)
    return envelopes_show(settings, f"Spent {fs.cash(number, settings)} from {key}; {fs.cash(env['left'], settings)} left.")


def envelopes_show(settings: Settings, said: str = "") -> screen.Shown | str:
    found = fs.rows(settings, fs.ENVELOPES)
    if not found:
        return "No cash envelopes yet. Say something like 'put 200 in a groceries envelope'."
    rows = [fs.meter(k, e.get("left", 0), e.get("amount", 0) or 1, settings, note=f"{fs.cash(e.get('left', 0), settings)} left of {fs.cash(e.get('amount', 0), settings)}")
            for k, e in sorted(found.items())]
    for r in rows:
        r["over"] = False
    said = said or "Envelopes: " + "; ".join(f"{k} {fs.cash(e.get('left', 0), settings)} left" for k, e in sorted(found.items())) + "."
    return fs.board(said, "Cash envelopes", "finance-envelopes", [fs.section("meters", "Left in each", rows=rows)])


# Net worth

def _items(value, what: str) -> dict[str, float]:
    out = {}
    for item in value or []:
        if isinstance(item, dict) and hs.clean(item.get("name")):
            out[hs.clean(item["name"], 40)] = fs.amount(item.get("amount"), f"{what} amount")
    return out


def networth_add(settings: Settings, day, assets, liabilities) -> screen.Shown:
    when = hs.parse_day(day).isoformat()
    assets, liabilities = _items(assets, "asset"), _items(liabilities, "liability")
    if not assets and not liabilities:
        raise ValueError("Tell me the assets (savings, pension, house) and liabilities (loans, cards) with amounts.")
    snaps = fs.rows(settings, fs.NETWORTH)
    if when not in snaps and len(snaps) >= 400:
        raise ValueError("The net worth log is full.")
    snaps[when] = {"assets": assets, "liabilities": liabilities}
    hs.save(settings, fs.NETWORTH, dict(sorted(snaps.items())))
    return networth_show(settings)


def _net(snap: dict) -> tuple[float, float]:
    return sum((snap.get("assets") or {}).values()), sum((snap.get("liabilities") or {}).values())


def networth_show(settings: Settings) -> screen.Shown | str:
    snaps = dict(sorted(fs.rows(settings, fs.NETWORTH).items()))
    if not snaps:
        return "No net worth snapshots yet. Tell me your assets and debts on a date."
    days = list(snaps)
    nets = [_net(snaps[d])[0] - _net(snaps[d])[1] for d in days]
    have, owe = _net(snaps[days[-1]])
    said = f"Net worth on {hs.spoken(hs.parse_day(days[-1]))}: {fs.cash(nets[-1], settings)}."
    if len(nets) > 1:
        change = nets[-1] - nets[-2]
        said += f" That's {'up' if change >= 0 else 'down'} {fs.cash(abs(change), settings)} since {days[-2]}."
    detail = [[k, "asset", f"{v:,.2f}"] for k, v in snaps[days[-1]]["assets"].items()] + \
             [[k, "liability", f"{v:,.2f}"] for k, v in snaps[days[-1]]["liabilities"].items()]
    return fs.board(said, "Net worth", "finance-networth", [
        fs.stats([("Assets", fs.cash(have, settings)), ("Liabilities", fs.cash(owe, settings)),
                  ("Net worth", fs.cash(nets[-1], settings))], f"On {days[-1]}"),
        fs.chart(days, nets, "line", title="Net worth over time"),
        fs.table(["Item", "Type", settings.currency], detail, "Latest snapshot")])


# Receipts

def receipt_add(settings: Settings, args: dict) -> str:
    log = hs.load(settings, fs.RECEIPTS, [])
    if len(log) >= fs.MAX_LOG:
        raise ValueError("The receipt log is full.")
    entry = {"shop": hs.need(args.get("shop"), "shop", 60), "amount": fs.amount(args.get("amount")),
             "date": hs.parse_day(args.get("date")).isoformat(), "item": hs.clean(args.get("item"), 80),
             "photo": hs.clean(args.get("photo"), 120), "folder": hs.clean(args.get("folder"), 80)}
    if args.get("warranty_months"):
        entry["warranty_months"] = int(hs.number(args["warranty_months"], "warranty months", 1, 240))
    log.append(entry)
    hs.save(settings, fs.RECEIPTS, log)
    what = f" for {entry['item']}" if entry["item"] else ""
    return f"Saved the {entry['shop']} receipt{what}: {fs.cash(entry['amount'], settings)} on {entry['date']}."


def _warranty_end(r: dict) -> str:
    if not r.get("warranty_months"):
        return ""
    d = hs.parse_day(r["date"])
    y, m = divmod(d.month - 1 + r["warranty_months"], 12)
    return f"{d.year + y:04d}-{m + 1:02d}-{min(d.day, 28):02d}"


def receipt_find(settings: Settings, query) -> screen.Shown | str:
    words = hs.clean(query).lower().split()
    log = [r for r in hs.load(settings, fs.RECEIPTS, []) if isinstance(r, dict)]
    found = [r for r in log if all(w in f"{r.get('shop')} {r.get('item')} {r.get('date')}".lower() for w in words)]
    if not found:
        return f"No receipts match {hs.clean(query)}." if words else "No receipts saved yet."
    found.sort(key=lambda r: r.get("date", ""), reverse=True)
    if len(found) == 1 and found[0].get("photo"):
        r = found[0]
        try:
            path = screen.find_file(settings, r.get("folder") or "", r["photo"])
        except ValueError:
            path = None
        if path:
            return screen.Shown(_receipt_line(settings, r) + " Here's the photo.", screen.file_card(settings, path))
    rows = [[r.get("date", ""), r.get("shop", ""), r.get("item", ""), f"{r.get('amount', 0):,.2f}",
             _warranty_end(r), r.get("photo", "")] for r in found]
    said = f"{hs.plural(len(found), 'receipt')} found. Latest: " + _receipt_line(settings, found[0])
    return fs.board(said, "Receipts", "finance-receipts",
                    [fs.table(["Date", "Shop", "Item", settings.currency, "Warranty to", "Photo"], rows)])


def _receipt_line(settings: Settings, r: dict) -> str:
    what = f" for {r['item']}" if r.get("item") else ""
    until = f", warranty until {_warranty_end(r)}" if r.get("warranty_months") else ""
    return f"{r['shop']}{what}, {fs.cash(r['amount'], settings)} on {r['date']}{until}."


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    pair = {"type": "array", "items": {"type": "object", "properties": {"name": text, "amount": {"type": "number"}},
                                       "required": ["name", "amount"], "additionalProperties": False}}
    return [{
        "name": "money_pots",
        "description": "Savings pots, cash envelopes, net worth and receipts. pot_create (name, target), pot_add / "
                       "pot_withdraw (name, amount), pots shows progress bars, pot_remove (confirmed true only after "
                       "the user agrees). envelope_set (name, amount; refills it), envelope_spend (name, amount, "
                       "what), envelopes. networth_add (date, assets and liabilities as name + amount), networth "
                       "shows the chart over time. receipt_add (shop, amount, date, item, warranty_months, photo = "
                       "file name of a receipt photo in a memory folder, folder), receipt_find (query: shop, item "
                       "or date) for returns and warranty claims.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["pot_create", "pot_add", "pot_withdraw", "pots", "pot_remove",
                                                      "envelope_set", "envelope_spend", "envelopes", "networth_add",
                                                      "networth", "receipt_add", "receipt_find"]},
                "name": text, "amount": {"type": "number"}, "target": {"type": "number"}, "what": text,
                "date": {"type": "string", "description": "YYYY-MM-DD, default today."},
                "assets": pair, "liabilities": pair,
                "shop": text, "item": text, "warranty_months": {"type": "integer"}, "photo": text, "folder": text,
                "query": text, "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"money_pots"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    actions = {
        "pot_create": lambda: pot_create(settings, a("name"), a("target") if a("target") is not None else a("amount")),
        "pot_add": lambda: pot_move(settings, a("name"), a("amount"), 1),
        "pot_withdraw": lambda: pot_move(settings, a("name"), a("amount"), -1),
        "pots": lambda: pots_show(settings),
        "pot_remove": lambda: pot_remove(settings, a("name"), bool(a("confirmed"))),
        "envelope_set": lambda: envelope_set(settings, a("name"), a("amount")),
        "envelope_spend": lambda: envelope_spend(settings, a("name"), a("amount"), a("what")),
        "envelopes": lambda: envelopes_show(settings),
        "networth_add": lambda: networth_add(settings, a("date"), a("assets"), a("liabilities")),
        "networth": lambda: networth_show(settings),
        "receipt_add": lambda: receipt_add(settings, args),
        "receipt_find": lambda: receipt_find(settings, a("query")),
    }
    if a("action") not in actions:
        raise ValueError("Unknown pots action.")
    return actions[a("action")]()
