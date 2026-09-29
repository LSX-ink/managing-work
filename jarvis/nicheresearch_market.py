"""Market side of niche research: a competitor tracker (names and notes you type), a pricing research log of prices you saw,
a SWOT builder pop-up and one optional "interest over time" check using Wikipedia page views.

Data is in nicheresearch.json in the memory folder. Competitors are just notes: no site is visited or scraped. The only
network use is interest_over_time, which sends the topic word to the free Wikimedia pageviews API (no key) and nothing else.
Wikipedia views are a rough interest signal only, not search volume or proof of demand.
"""

from datetime import timedelta
from statistics import mean, median
from urllib.parse import quote

import httpx

import nicheresearch_store as nr
import screen
from config import Settings

NAMES = {"nicheresearch_market"}
API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{}/monthly/{}/{}"
SWOT_KEYS = {"strength": "strengths", "weakness": "weaknesses", "opportunity": "opportunities", "threat": "threats"}
SWOT_PROMPTS = {
    "strengths": ["What do you already know or own that helps?", "What could you do faster or better than most?", "What do people say you are good at?"],
    "weaknesses": ["What skills or tools are you missing?", "What would you avoid doing?", "Where might you run out of time or money?"],
    "opportunities": ["What do competitors' reviews complain about?", "Which topics are covered badly or not at all?", "What is growing or changing in this area?"],
    "threats": ["Who could copy you easily?", "What could change: rules, platforms, prices?", "What if interest fades in a year?"],
}
INTEREST_NOTE = "Wikipedia views are a rough interest signal only: not search volume, not demand, and not a sales forecast."


def _comp(row: dict, args: dict) -> dict:
    return nr.pick(row["competitors"], args.get("competitor"), "name", "competitor")


def competitor_add(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if len(row["competitors"]) >= nr.MAX_ROWS:
        raise ValueError("The competitor list is full.")
    c = {"id": nr.next_id(row["competitors"]), "name": nr.need(args.get("name"), "competitor name", 60), "strengths": nr.clean(args.get("strengths"), 200),
         "weaknesses": nr.clean(args.get("weaknesses"), 200), "prices": nr.clean(args.get("prices"), 120),
         "topics": nr.items(args.get("topics")), "notes": nr.clean(args.get("notes"), 300), "added": nr.today().isoformat()}
    row["competitors"].append(c)
    nr.save(settings, nr.FILE, d)
    return f"Added competitor {c['id']}, {c['name']}, to {row['name']}."


def competitor_update(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    c = _comp(row, args)
    for key, limit in (("strengths", 200), ("weaknesses", 200), ("prices", 120), ("notes", 300)):
        if args.get(key) is not None:
            c[key] = nr.clean(args[key], limit)
    if args.get("topics") is not None:
        c["topics"] = nr.items(args["topics"])
    if args.get("name"):
        c["name"] = nr.need(args["name"], "competitor name", 60)
    nr.save(settings, nr.FILE, d)
    return f"Updated {c['name']}."


def competitor_remove(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    c = _comp(row, args)
    ask = nr.confirm_first(args, f"the competitor {c['name']}")
    if ask:
        return ask
    row["competitors"] = [x for x in row["competitors"] if x is not c]
    nr.save(settings, nr.FILE, d)
    return f"Removed {c['name']}."


def competitor_list(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if not row["competitors"]:
        raise ValueError(f"No competitors noted for {row['name']} yet.")
    rows = [[str(c["id"]), c["name"], c["strengths"], c["weaknesses"], c["prices"], str(len(c["topics"]))] for c in row["competitors"]]
    return nr.table(f"{len(rows)} competitors for {row['name']}.", f"Competitors: {row['name']}",
                    ["#", "Name", "Strengths", "Weaknesses", "Prices", "Topics"], rows)


def competitor_compare(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if len(row["competitors"]) < 2:
        raise ValueError("Note at least two competitors to compare.")
    secs = [(c["name"], [f"Strengths: {c['strengths'] or '-'}", f"Weaknesses: {c['weaknesses'] or '-'}", f"Prices: {c['prices'] or '-'}"]
             + ([f"Notes: {c['notes']}"] if c["notes"] else [])) for c in row["competitors"]]
    weak = [f"{c['name']}: {c['weaknesses']}" for c in row["competitors"] if c["weaknesses"]]
    secs.append(("Openings to aim at (their weaknesses)", weak or ["Note some weaknesses to see openings."]))
    return nr.sheet(f"Compared {len(row['competitors'])} competitors.", f"Competitor comparison: {row['name']}", secs,
                    "Based on your own notes. Look at real products and reviews yourself before deciding.")


def price_add(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    p = {"id": nr.next_id(row["prices"]), "item": nr.need(args.get("item"), "what was priced", 80), "price": nr.number(args.get("price"), "price", 0, 1_000_000),
         "seller": nr.clean(args.get("seller"), 60), "date": (nr.parse_date(args.get("date"), "date") or nr.today()).isoformat(), "note": nr.clean(args.get("notes"), 200)}
    row["prices"].append(p)
    nr.save(settings, nr.FILE, d)
    return f"Logged {p['item']} at {nr.gbp(p['price'])}. That is {len(row['prices'])} prices for {row['name']}."


def price_remove(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    p = nr.pick(row["prices"], args.get("price_ref"), "item", "price entry")
    ask = nr.confirm_first(args, f"the price entry {p['item']}")
    if ask:
        return ask
    row["prices"] = [x for x in row["prices"] if x is not p]
    nr.save(settings, nr.FILE, d)
    return "Removed that price entry."


def price_list(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if not row["prices"]:
        raise ValueError(f"No prices logged for {row['name']} yet. Say what you saw and for how much.")
    rows = [[str(p["id"]), p["item"], nr.gbp(p["price"]), p["seller"], p["date"]] for p in sorted(row["prices"], key=lambda p: p["price"])]
    return nr.table(f"{len(rows)} prices seen for {row['name']}.", f"Prices seen: {row['name']}", ["#", "Item", "Price", "Seller", "Date"], rows)


def _range(row: dict) -> list[float]:
    prices = sorted(p["price"] for p in row["prices"])
    if len(prices) < 2:
        raise ValueError(f"Log at least two prices for {row['name']} first.")
    return prices


def price_stats(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    prices = _range(row)
    card = screen.card("chart", f"Prices seen: {row['name']}", "", chart={
        "type": "bar", "labels": [p["item"][:20] for p in sorted(row["prices"], key=lambda p: p["price"])], "values": prices, "unit": "£"})
    return screen.Shown(f"Lowest {nr.gbp(prices[0])}, middle {nr.gbp(median(prices))}, average {nr.gbp(round(mean(prices), 2))}, highest {nr.gbp(prices[-1])}. "
                        "These are prices you saw, not proof of what sells.", card)


def price_position(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    prices = _range(row)
    mine = nr.number(args.get("my_price"), "your price", 0, 1_000_000)
    below = sum(1 for p in prices if p < mine)
    share = round(below / len(prices) * 100)
    word = "budget end" if share < 25 else "middle" if share < 75 else "premium end"
    lo, hi = prices[0], prices[-1]
    return nr.sheet(f"At {nr.gbp(mine)} you would sit at the {word}.", "Where my price sits", [
        ("Your price", [f"{nr.gbp(mine)} is above {share}% of the {len(prices)} prices you logged"]),
        ("Range you logged", [f"{nr.gbp(lo)} to {nr.gbp(hi)}, middle {nr.gbp(median(prices))}"]),
        ("Ask yourself", ["Is there a reason to be cheaper or dearer: quality, extras, a narrower audience?",
                          "Would a premium price need proof, such as reviews or results?"])],
        "Prices you saw only show what others charge. Test what real people will pay.", headline=word)


def _quad(value):
    text = nr.clean(value).lower()
    return next((full for short, full in SWOT_KEYS.items() if text and text.startswith(short[:5])), None)


def swot_add(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    key = _quad(args.get("quadrant"))
    if key is None:
        raise ValueError("Which box: strength, weakness, opportunity or threat?")
    added = nr.items(args.get("text"))
    if not added:
        raise ValueError("What should I add?")
    row["swot"][key] = (row["swot"][key] + added)[:20]
    nr.save(settings, nr.FILE, d)
    return f"Added to {key} for {row['name']}."


def swot_show(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if not any(row["swot"].values()):
        raise ValueError(f"The SWOT for {row['name']} is empty. Say a strength, weakness, opportunity or threat.")
    card = screen.card(nr.SWOT, f"SWOT: {row['name']}", "", data={"name": row["name"], "boxes": [
        {"title": k.title(), "items": v, "say": f"Give me SWOT prompts for {k}"} for k, v in row["swot"].items()]})
    return screen.Shown(f"SWOT for {row['name']}: {sum(len(v) for v in row['swot'].values())} points.", card)


def swot_prompts(settings: Settings, args: dict):
    key = _quad(args.get("quadrant"))
    boxes = [key] if key else list(SWOT_PROMPTS)
    return nr.sheet("Questions to fill in your SWOT.", "SWOT prompts", [(k.title(), SWOT_PROMPTS[k]) for k in boxes],
                    "Strengths and weaknesses are about you; opportunities and threats are outside you.")


def swot_clear(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    ask = nr.confirm_first(args, f"the whole SWOT for {row['name']}")
    if ask:
        return ask
    row["swot"] = nr.new_niche("x")["swot"]
    nr.save(settings, nr.FILE, d)
    return f"Cleared the SWOT for {row['name']}."


async def interest_over_time(settings: Settings, args: dict, http):
    topic = nr.need(args.get("topic") or args.get("name"), "topic word", 60)
    end = nr.today().replace(day=1) - timedelta(days=1)
    start = (end.replace(day=1) - timedelta(days=330)).replace(day=1)
    url = API.format(quote(topic.replace(" ", "_"), safe=""), start.strftime("%Y%m0100"), end.strftime("%Y%m0100"))
    try:
        resp = await http.get(url, headers={"User-Agent": "Alfred-assistant/1.0"}, timeout=10)
    except httpx.HTTPError:
        raise ValueError("I couldn't reach Wikipedia just now. Try again later.") from None
    if resp.status_code == 404:
        raise ValueError(f"Wikipedia has no page called {topic}. Try the exact title of a Wikipedia article.")
    if resp.status_code != 200:
        raise ValueError("Wikipedia's page view service didn't answer properly. Try again later.")
    try:
        found = [(str(i["timestamp"])[:6], int(i["views"])) for i in resp.json()["items"]]
    except (ValueError, KeyError, TypeError):
        raise ValueError("Wikipedia's answer wasn't what I expected.") from None
    if not found:
        raise ValueError(f"No page view figures for {topic}.")
    labels = [f"{t[:4]}-{t[4:]}" for t, _ in found]
    values = [v for _, v in found]
    half = len(values) // 2
    a, b = sum(values[:half]), sum(values[half:])
    trend = "rising" if b > a * 1.15 else "falling" if b < a * 0.85 else "steady"
    card = screen.card("chart", f"Wikipedia views: {topic}", "", chart={"type": "line", "labels": labels, "values": values, "unit": ""})
    return screen.Shown(f"Wikipedia views for {topic} look {trend} over {len(values)} months. {INTEREST_NOTE}", card)


ACTIONS = {"competitor_add": competitor_add, "competitor_update": competitor_update, "competitor_remove": competitor_remove,
           "competitor_list": competitor_list, "competitor_compare": competitor_compare, "price_add": price_add,
           "price_list": price_list, "price_stats": price_stats, "price_position": price_position, "price_remove": price_remove,
           "swot_add": swot_add, "swot_show": swot_show, "swot_prompts": swot_prompts, "swot_clear": swot_clear}


def tool_definitions() -> list[dict]:
    return [{
        "name": "nicheresearch_market",
        "description": "Market research notes for a niche before spending money: competitor tracker (strengths, weaknesses, prices, topics the "
                       "user types), competitor comparison, pricing research log with stats and where the user's price sits, SWOT builder "
                       "pop-up, and interest_over_time (Wikipedia page views for a topic word, rough signal only). No sites are visited. "
                       "Set confirmed only after the user agrees to any remove or clear action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [*ACTIONS, "interest_over_time"]},
                "niche": {"type": "string", "description": "Niche number or name (optional when there is only one)."},
                "competitor": {"type": "string", "description": "Competitor number or name."}, "name": {"type": "string"},
                "strengths": {"type": "string"}, "weaknesses": {"type": "string"}, "prices": {"type": "string", "description": "Their prices, as typed."},
                "topics": {"type": "string", "description": "Topics they cover, comma separated."}, "notes": {"type": "string"},
                "item": {"type": "string", "description": "What was priced."}, "price": {"type": "number", "description": "Price in pounds."},
                "seller": {"type": "string"}, "date": {"type": "string", "description": "YYYY-MM-DD."}, "price_ref": {"type": "string", "description": "Price entry number or item."},
                "my_price": {"type": "number"}, "quadrant": {"type": "string", "enum": ["strength", "weakness", "opportunity", "threat"]},
                "text": {"type": "string", "description": "SWOT point(s), comma or line separated."},
                "topic": {"type": "string", "description": "interest_over_time: one topic word or Wikipedia title."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    if args.get("action") == "interest_over_time":
        if http is None:
            raise ValueError("I can't look that up right now.")
        return await interest_over_time(settings, args, http)
    return nr.dispatch(ACTIONS, settings, args)
