"""Investing basics part 4: a paper-only practice portfolio.

The user types made-up holdings and prices; there are no live prices, no network and no real money. It teaches how a
portfolio, allocation, gains, falls and rebalancing work. It never suggests what to buy or sell.
"""

import homestore as hs
import investlearn_store as st
import screen
from config import Settings

NAMES = {"invest_practice"}
NOTE = st.PRACTICE + " " + st.DISCLAIMER


def _need(data: dict) -> None:
    if not data["holdings"]:
        raise ValueError("Your practice portfolio is empty. Add a made-up holding, for example: practice 10 units of Example Fund at 5 pounds.")


def _find(data: dict, name) -> dict:
    _need(data)
    holdings = {h["name"]: h for h in data["holdings"]}
    found = hs.find(holdings, hs.need(name, "holding"))
    if found is None:
        raise ValueError(f"I can't find {hs.clean(name)} in your practice portfolio.")
    return holdings[found]


def _value(h: dict) -> float:
    return h["units"] * h["price"]


def _total(data: dict) -> float:
    return sum(_value(h) for h in data["holdings"])


def _log(data: dict, kind: str, h: dict, units: float, price: float, note: str = "") -> None:
    st.put(data["trades"], {"id": st.new_id(data), "date": hs.today().isoformat(), "kind": kind, "name": h["name"], "units": units,
                            "price": price, "note": note})
    del data["trades"][:-200]


def add_holding(settings: Settings, args: dict):
    data = st.load(settings)
    name = hs.need(args.get("name"), "holding name", 40)
    units, buy = st.num(args, "units", "number of units", None, 0.0001), st.num(args, "buy_price", "buy price", None, 0.0001)
    price = st.num(args, "price", "current price", buy, 0.0001)
    holdings = {h["name"].lower(): h for h in data["holdings"]}
    h = holdings.get(name.lower())
    if h is None:
        h = {"id": st.new_id(data), "name": name, "units": 0.0, "cost": 0.0, "price": price}
        st.put(data["holdings"], h)
    paid = h["units"] * h["cost"] + units * buy
    h["units"] += units
    h["cost"] = paid / h["units"]
    h["price"] = price
    _log(data, "buy", h, units, buy)
    st.save(settings, data)
    return show(settings, {}, f"Added {units:g} units of {h['name']}. ")


def set_price(settings: Settings, args: dict):
    data = st.load(settings)
    h = _find(data, args.get("name"))
    h["price"] = st.num(args, "price", "price", None, 0.0001)
    st.save(settings, data)
    return show(settings, {}, f"{h['name']} price set to {st.gbp2(h['price'])}. ")


def show(settings: Settings, args: dict, lead: str = ""):
    data = st.load(settings)
    _need(data)
    total = _total(data)
    cost = sum(h["units"] * h["cost"] for h in data["holdings"])
    rows = [[h["name"], f"{h['units']:g}", st.gbp2(h["cost"]), st.gbp2(h["price"]), st.gbp2(_value(h)), f"{_value(h) - h['units'] * h['cost']:+,.2f}"] for h in data["holdings"]]
    rows.append(["Total", "", "", "", st.gbp2(total), f"{total - cost:+,.2f}"])
    text = f"{lead}Practice portfolio: made-up value {st.gbp2(total)}, {total - cost:+,.2f} against what you typed as paid. {NOTE}"
    return screen.Shown(text, screen.card("table", "Practice portfolio (made-up)", "investlearn-practice", columns=["Holding", "Units", "Paid", "Price", "Value", "Gain/loss"], rows=rows,
                                          text=NOTE, buttons=[{"label": "Allocation", "say": "Show my practice portfolio allocation."},
                                                              {"label": "What if it falls?", "say": "What if my practice portfolio fell 20 percent?"}]))


def allocation(settings: Settings, args: dict):
    data = st.load(settings)
    _need(data)
    total = _total(data) or 1
    ranked = sorted(data["holdings"], key=_value, reverse=True)
    rows = [{"label": h["name"], "value": _value(h), "max": total, "text": f"{100 * _value(h) / total:.0f}% ({st.gbp2(_value(h))})", "warn": _value(h) / total > 0.5} for h in ranked]
    top = 100 * _value(ranked[0]) / total
    verdict = "One holding is more than half, so this practice mix is concentrated." if top > 50 else "No single holding is more than half of this practice mix."
    return screen.Shown(f"{verdict} {NOTE}", st.bars_card("Practice allocation", "investlearn-practice-allocation", rows, NOTE))


def what_if(settings: Settings, args: dict):
    data = st.load(settings)
    _need(data)
    fall = st.num(args, "fall", "fall in percent", None, -500, 99.9)
    total = _total(data)
    after = total * (1 - fall / 100)
    need = fall / (100 - fall) * 100 if fall > 0 else 0
    text = f"Practice what-if: a {fall:g}% move takes made-up {st.gbp2(total)} to {st.gbp2(after)}." + (f" You'd need a gain of about {need:.1f}% to recover. " if fall > 0 else " ") + NOTE
    rows = [{"label": "Now", "value": total, "max": max(total, after) or 1, "text": st.gbp2(total)},
            {"label": f"After {fall:g}%", "value": max(after, 0), "max": max(total, after) or 1, "text": st.gbp2(after), "warn": fall > 0}]
    return screen.Shown(text, st.bars_card("Practice what-if", "investlearn-practice-whatif", rows, NOTE))


def sell(settings: Settings, args: dict):
    data = st.load(settings)
    h = _find(data, args.get("name"))
    units = st.num(args, "units", "number of units", h["units"], 0.0001)
    if units > h["units"] + 1e-9:
        raise ValueError(f"You only hold {h['units']:g} units of {h['name']} in the practice portfolio.")
    price = st.num(args, "price", "sell price", h["price"], 0.0001)
    gain = units * (price - h["cost"])
    h["units"] -= units
    h["price"] = price
    _log(data, "sell", h, units, price, f"{gain:+.2f}")
    if h["units"] <= 1e-9:
        data["holdings"].remove(h)
    st.save(settings, data)
    return f"Practice sale: {units:g} units of {h['name']} at {st.gbp2(price)}, made-up {'gain' if gain >= 0 else 'loss'} {st.gbp2(abs(gain))}. {st.PRACTICE}"


def remove_holding(settings: Settings, args: dict):
    data = st.load(settings)
    h = _find(data, args.get("name"))
    if args.get("confirmed") is not True:
        return st.confirm_needed(f"removing {h['name']} from the practice portfolio")
    data["holdings"].remove(h)
    st.save(settings, data)
    return f"Removed {h['name']} from the practice portfolio."


def reset(settings: Settings, args: dict):
    if args.get("confirmed") is not True:
        return st.confirm_needed("clearing the whole practice portfolio and its log")
    data = st.load(settings)
    data["holdings"], data["trades"] = [], []
    st.save(settings, data)
    return "Practice portfolio cleared."


def trade_log(settings: Settings, args: dict):
    data = st.load(settings)
    if not data["trades"]:
        raise ValueError("No practice trades yet.")
    rows = [[t["date"], t["kind"], t["name"], f"{t['units']:g}", st.gbp2(t["price"]), t.get("note", "")] for t in reversed(data["trades"][-50:])]
    return screen.Shown(f"{len(data['trades'])} practice trades logged. {st.PRACTICE}",
                        screen.card("table", "Practice trade log", "investlearn-practice-log", columns=["Date", "Type", "Holding", "Units", "Price", "Gain/loss"], rows=rows, text=st.PRACTICE))


def diversification_check(settings: Settings, args: dict):
    data = st.load(settings)
    _need(data)
    total = _total(data) or 1
    top = max(data["holdings"], key=_value)
    share = 100 * _value(top) / total
    count = len(data["holdings"])
    notes = [f"{count} practice holding{'s' if count != 1 else ''}.", f"Largest is {top['name']} at {share:.0f}% of the total."]
    notes.append("Few holdings and one big one means a single failure hurts a lot." if count < 5 or share > 40 else "Spread looks wide, but holdings of the same kind can still fall together.")
    body = "\n".join(notes) + "\n\nDiversification reduces the damage from one thing failing; it cannot remove the risk that markets fall together.\n\n" + NOTE
    return screen.Shown(" ".join(notes) + " " + NOTE, screen.card("text", "Practice diversification check", "investlearn-practice-diversify", text=body))


def rebalance(settings: Settings, args: dict):
    data = st.load(settings)
    _need(data)
    targets = args.get("targets") or []
    if not targets:
        raise ValueError("Give me target percentages, for example Fund A 60 and Fund B 40.")
    total = _total(data)
    wanted = {}
    for t in targets[:20]:
        h = _find(data, t.get("name"))
        wanted[h["name"]] = hs.number(t.get("percent"), "target percent", 0, 100)
    if abs(sum(wanted.values()) - 100) > 0.5:
        raise ValueError("The target percentages should add up to 100.")
    rows = []
    for h in data["holdings"]:
        if h["name"] not in wanted:
            continue
        now, goal = 100 * _value(h) / (total or 1), wanted[h["name"]]
        move = total * goal / 100 - _value(h)
        rows.append([h["name"], f"{now:.0f}%", f"{goal:g}%", f"{'move in' if move >= 0 else 'move out'} {st.gbp2(abs(move))}"])
    return screen.Shown(f"Practice rebalancing shows how far each holding has drifted from the split you typed. {NOTE}",
                        screen.card("table", "Practice rebalancing", "investlearn-practice-rebalance", columns=["Holding", "Now", "Target", "To rebalance"], rows=rows,
                                    text="Rebalancing means nudging back to a planned mix. It is an idea to learn, not a recommendation. " + NOTE))


ACTIONS = {"add_holding": add_holding, "set_price": set_price, "show": show, "allocation": allocation, "what_if": what_if,
           "sell": sell, "remove_holding": remove_holding, "reset": reset, "trade_log": trade_log,
           "diversification_check": diversification_check, "rebalance": rebalance}


def tool_definitions() -> list[dict]:
    number = {"type": "number"}
    return [{
        "name": "invest_practice",
        "description": "A paper-only PRACTICE portfolio for learning: the user types made-up holdings and prices; no live prices, no real money, "
                       "never advice on what to buy. action: add_holding (name, units, buy_price, price) / set_price (name, price) / show / "
                       "allocation / what_if (fall percent) / sell (name, units, price) / remove_holding (name, confirmed only after yes) / "
                       "reset (confirmed only after yes) / trade_log / diversification_check / rebalance (targets = list of {name, percent}).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "name": {"type": "string"}, "units": number, "buy_price": number, "price": number, "fall": number,
                "targets": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "percent": number},
                                                       "required": ["name", "percent"], "additionalProperties": False}},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = ACTIONS.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
