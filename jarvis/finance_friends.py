"""IOUs and bill splitting with friends: who owes whom, settling up, and the fewest payments to clear a group.

A ledger in finance-ious.json in the memory folder; each line is "A owes B amount". The user is "Me".
Amounts are in the user's currency.
"""

from collections import defaultdict

import finance_store as fs
import homestore as hs
import screen
from config import Settings

ME = {"me", "i", "myself", "you", "user"}


def _who(value, what: str = "person") -> str:
    name = hs.need(value, what, 40)
    return "Me" if name.lower() in ME else name.title()


def _ledger(settings: Settings) -> list[dict]:
    return [e for e in hs.load(settings, fs.IOUS, []) if isinstance(e, dict) and e.get("amount")]


def _add(settings: Settings, entries: list[dict]) -> None:
    ledger = _ledger(settings) + entries
    if len(ledger) > fs.MAX_LOG:
        raise ValueError("The IOU list is full.")
    hs.save(settings, fs.IOUS, ledger)


def _entry(debtor: str, creditor: str, amount: float, what: str, kind: str = "iou") -> dict:
    return {"date": hs.today().isoformat(), "owes": debtor, "to": creditor, "amount": round(amount, 2),
            "what": hs.clean(what, 60), "kind": kind}


def owe(settings: Settings, debtor, creditor, value, what) -> str:
    debtor, creditor = _who(debtor, "person who owes"), _who(creditor or "me", "person owed")
    if debtor == creditor:
        raise ValueError("Someone can't owe themselves.")
    number = fs.amount(value)
    _add(settings, [_entry(debtor, creditor, number, what)])
    return f"Noted: {_say(debtor)} {_owes(debtor)} {_say(creditor, True)} {fs.cash(number, settings)}" + \
        (f" for {hs.clean(what, 60)}." if hs.clean(what) else ".")


def split(settings: Settings, payer, value, people, what) -> str:
    payer = _who(payer or "me", "person who paid")
    group = []
    for p in [payer] + [_who(x) for x in people or []]:
        if p not in group:
            group.append(p)
    if len(group) < 2:
        raise ValueError("Who was the bill split with?")
    total = fs.amount(value)
    share = round(total / len(group), 2)
    _add(settings, [_entry(p, payer, share, what, "split") for p in group if p != payer])
    return (f"Split {fs.cash(total, settings)} {len(group)} ways: {fs.cash(share, settings)} each, "
            f"owed to {_say(payer, True)}.")


def _say(name: str, obj: bool = False) -> str:
    return ("me" if obj else "you") if name == "Me" else name


def _owes(name: str) -> str:
    return "owe" if name == "Me" else "owes"


def balances(settings: Settings) -> dict[str, float]:
    net = defaultdict(float)
    for e in _ledger(settings):
        net[e["to"]] += e["amount"]
        net[e["owes"]] -= e["amount"]
    return {k: round(v, 2) for k, v in net.items() if abs(v) >= 0.01}


def simplify(net: dict[str, float]) -> list[tuple[str, str, float]]:
    """The fewest payments that clear everyone: biggest debtor pays biggest creditor, repeatedly."""
    owed = sorted(((v, k) for k, v in net.items() if v > 0), reverse=True)
    owing = sorted(((-v, k) for k, v in net.items() if v < 0), reverse=True)
    moves = []
    while owed and owing:
        (credit, c), (debt, d) = owed[0], owing[0]
        pay = round(min(credit, debt), 2)
        moves.append((d, c, pay))
        owed[0], owing[0] = (credit - pay, c), (debt - pay, d)
        owed = sorted((x for x in owed if x[0] >= 0.01), reverse=True)
        owing = sorted((x for x in owing if x[0] >= 0.01), reverse=True)
    return moves


def _line(settings: Settings, d: str, c: str, pay: float) -> str:
    return f"{_say(d)} {_owes(d)} {_say(c, True)} {fs.cash(pay, settings)}"


def show(settings: Settings, simplified: bool) -> screen.Shown | str:
    net = balances(settings)
    if not net:
        return "Nobody owes anybody anything."
    moves = simplify(net)
    items = [{"label": _line(settings, d, c, pay), "say": f"{_say(d)} paid {_say(c, True)} {pay:.2f}, settle it."}
             for d, c, pay in moves]
    if simplified:
        said = f"{hs.plural(len(moves), 'payment')} would clear everything: " + \
            "; ".join(_line(settings, d, c, p) for d, c, p in moves) + "."
        return screen.Shown(said, screen.card("list", "Settle up", "finance-simplify", items=items))
    mine = net.get("Me", 0.0)
    said = (f"Overall you're owed {fs.cash(mine, settings)}." if mine > 0 else
            f"Overall you owe {fs.cash(-mine, settings)}." if mine < 0 else "You're square.")
    rows = [[k, f"{v:+,.2f}", "is owed" if v > 0 else "owes"] for k, v in sorted(net.items(), key=lambda kv: -kv[1])]
    return fs.board(said, "IOUs", "finance-ious", [
        fs.table(["Person", settings.currency, ""], rows, "Balances"),
        fs.section("list", "Simplest way to settle", items=items)],
        buttons=[{"label": "Simplify", "say": "Simplify the debts between my friends."}])


def settle(settings: Settings, payer, payee, value) -> str:
    payer, payee = _who(payer, "person who paid"), _who(payee or "me", "person paid")
    pair = sum(e["amount"] if (e["owes"], e["to"]) == (payer, payee) else
               -e["amount"] if (e["owes"], e["to"]) == (payee, payer) else 0 for e in _ledger(settings))
    number = fs.amount(value) if value is not None else round(pair, 2)
    if number <= 0:
        return f"{_say(payer)} {'don' if payer == 'Me' else 'doesn'}'t owe {_say(payee, True)} anything."
    _add(settings, [_entry(payee, payer, number, "settled up", "paid")])
    left = round(pair - number, 2)
    rest = f" {_say(payer)} still {_owes(payer)} {fs.cash(left, settings)}." if left >= 0.01 else " All square now."
    return f"Recorded {_say(payer)} paying {_say(payee, True)} {fs.cash(number, settings)}.{rest}"


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "money_friends",
        "description": "IOUs and splitting bills with friends. The user is 'me'. owe: who owes whom (person = who "
                       "owes, to = who is owed, amount, what). split: someone paid a bill split equally (payer, "
                       "amount, people it was shared with, what). balances: who owes whom overall. settle: record a "
                       "payment (person paid 'to'; amount, default everything they owe). simplify: the fewest "
                       "payments to settle up a group.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["owe", "split", "balances", "settle", "simplify"]},
                "person": text, "to": text, "payer": text, "amount": {"type": "number"}, "what": text,
                "people": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"money_friends"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    actions = {
        "owe": lambda: owe(settings, a("person"), a("to"), a("amount"), a("what")),
        "split": lambda: split(settings, a("payer"), a("amount"), a("people"), a("what")),
        "balances": lambda: show(settings, False),
        "settle": lambda: settle(settings, a("person") or a("payer"), a("to"), a("amount")),
        "simplify": lambda: show(settings, True),
    }
    if a("action") not in actions:
        raise ValueError("Unknown IOU action.")
    return actions[a("action")]()
