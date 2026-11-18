"""Shopify store leads: detection, store checks, ranking, store makeover outreach and Shopify prices. No network:
every page and API answer is mocked."""

import asyncio
from dataclasses import replace
from urllib.parse import parse_qs

import httpx
import pytest

import kinetic_find as kf
import kinetic_reach as kr
import kinetic_sales as ks
import kinetic_store as st
import kinetic_world as world
import memory
from config import Settings
from test_kinetic import GOOD, YEAR, handler as base_handler, public_links  # noqa: F401 (autouse fixture)

TERMS = "half when we start building, half once everything's complete"
HEAD = f"""<title>Velvet Rose Boutique | Dresses and gifts</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta property="og:image" content="/og.jpg"><link rel="icon" href="/f.png">
<script type="application/ld+json">{{"@type": "Store", "name": "Velvet Rose"}}</script>"""
DAWN = f"""<!doctype html><html><head>{HEAD}
<meta name="description" content="Dresses and gifts in Manchester.">
<link rel="stylesheet" href="//cdn.shopify.com/s/files/1/base.css">
<script src="//cdn.shopify.com/s/files/1/global.js" defer></script>
<script src="https://www.googletagmanager.com/gtag/js?id=G-1" async></script>
<script>var Shopify = Shopify || {{}};
Shopify.theme = {{"name":"Copy of Dawn","id":1234,"schema_name":"Dawn","schema_version":"15.0.0","theme_store_id":887,"role":"main"}};
</script><style>:root{{--font-body-family: Assistant, sans-serif;}} body{{font-family: Assistant, sans-serif}}</style>
</head><body><h1>Velvet Rose</h1><section class="image-banner"><img src="/hero.jpg" alt="Shop"></section>
<img src="/a.jpg" alt="a"><img src="/b.jpg" alt="b"><img src="/c.jpg" alt="c" width="400" height="500">
<a href="tel:+441610000000">Call</a><a href="/pages/contact">Contact</a><p>© {YEAR} Velvet Rose</p></body></html>"""
PRESTIGE = f"""<!doctype html><html><head>{HEAD}
<meta name="description" content="Luxury hair.">
<script src="https://cdn.shopify.com/s/files/1/theme.js"></script>
<script src="https://cdn.judge.me/widget.js"></script>
<script>Shopify.theme = {{"name":"Prestige","id":99,"schema_name":"Prestige","role":"main"}};</script>
<style>@keyframes fade{{from{{opacity:0}}}} h1{{font-family:'Playfair Display', serif}}</style>
</head><body><h1>Crown Wigs</h1><video autoplay muted loop src="/hero.mp4"></video>
<div class="jdgm-widget"></div><a href="tel:+441610000001">Call</a><a href="/pages/contact">Contact</a>
<p>© {YEAR} Crown</p></body></html>"""
WIX = f"""<!doctype html><html><head>{HEAD}<meta name="description" content="Gifts.">
<script src="https://static.wixstatic.com/main.js"></script></head><body><h1>Wix Gifts</h1>
<a href="tel:+44">Call</a><form></form><p>© {YEAR}</p></body></html>"""
MENTION = f"""<!doctype html><html><head>{HEAD}<meta name="description" content="Pets."></head><body><h1>Paws</h1>
<a href="tel:+44">Call</a><form></form><p>Powered by Shopify · © {YEAR}</p></body></html>"""

STORES = [
    {"type": "node", "id": 11, "tags": {"name": "Crown Wigs", "shop": "wigs", "website": "https://crown.test"}},
    {"type": "node", "id": 12, "tags": {"name": "Velvet Rose", "shop": "boutique", "website": "https://velvet.test",
                                        "phone": "0161 000 0002", "addr:street": "Oldham St", "addr:housenumber": "7"}},
    {"type": "node", "id": 13, "tags": {"name": "Wix Gifts", "shop": "gift", "website": "https://wixgifts.test"}},
    {"type": "node", "id": 14, "tags": {"name": "Paws Ltd", "shop": "pet", "website": "https://paws.test"}},
]
PAGES = {"crown.test": PRESTIGE, "velvet.test": DAWN, "wixgifts.test": WIX, "paws.test": MENTION}
calls = []


def handler(request: httpx.Request) -> httpx.Response:
    host = request.url.host
    calls.append(request)
    if host == "overpass-api.de":
        calls.append(parse_qs(request.content.decode())["data"][0])
        return httpx.Response(200, json={"elements": STORES})
    if host == "www.googleapis.com":
        if request.headers.get("x-goog-api-key") != "speed-key":
            return httpx.Response(400)
        return httpx.Response(200, json={"lighthouseResult": {"categories": {"performance": {"score": 0.31}}}})
    if host == "paws.test" and request.url.path == "/products.json":
        return httpx.Response(200, json={"products": [{"id": 1, "title": "Rope toy"}]},
                              headers={"content-type": "application/json"})
    if host in PAGES and request.url.path in ("", "/"):
        extra = {"x-shopid": "42"} if host == "velvet.test" else {}
        return httpx.Response(200, text=PAGES[host], headers={"content-type": "text/html; charset=utf-8", **extra})
    return base_handler(request)


@pytest.fixture
def s(tmp_path):
    calls.clear()
    return Settings(memory_dir=str(tmp_path))


def finder(s, **args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await kf.run_tool("web_client_finder", args, s, http)
    return asyncio.run(go())


def sales(s, **args):
    return asyncio.run(ks.run_tool("web_design_sales", args, s))


def reach(s, **args):
    return asyncio.run(kr.run_tool("web_design_reach", args, s))


# ---- detection and store checks ---------------------------------------------------------

def test_detects_shopify_but_not_wix_or_a_plain_site():
    dawn = kf.shopify_check(DAWN, {}, "https://velvet.test")
    assert dawn["is_shopify"] and dawn["via"] == "page"
    assert not kf.shopify_check(WIX, {}, "https://wixgifts.test")["is_shopify"]
    plain = kf.shopify_check(GOOD, {}, "https://bloom.test")
    assert not plain["is_shopify"] and not plain["maybe"]
    by_header = kf.shopify_check("<html><body>Hi</body></html>", {"X-ShopId": "42"}, "https://x.test")
    assert by_header["is_shopify"] and by_header["via"] == "headers"
    only_theme = kf.shopify_check('<script>Shopify.theme = {"name":"Sense","role":"main"};</script>', {}, "")
    assert only_theme["is_shopify"] and only_theme["theme"] == "Sense" and only_theme["free_theme"]
    mention = kf.shopify_check(MENTION, {}, "https://paws.test")
    assert not mention["is_shopify"] and mention["maybe"]  # only worth a /products.json check


def test_theme_parsing_and_the_free_theme_flag():
    dawn = kf.shopify_check(DAWN, {}, "https://velvet.test")
    assert dawn["theme"] == "Copy of Dawn" and dawn["schema"] == "Dawn" and dawn["base_theme"] == "Dawn"
    assert dawn["free_theme"]
    prestige = kf.shopify_check(PRESTIGE, {}, "https://crown.test")
    assert prestige["theme"] == "Prestige" and not prestige["free_theme"]
    assert kf.theme_of('Shopify.theme = {"name":"Refresh \\"v2\\"","schema_name":"Refresh"};') == \
        ('Refresh "v2"', "Refresh")
    assert kf.theme_of("Shopify.theme = {broken: true};") == ("", "")
    for theme, free in (("Dawn", True), ("Colorblock", True), ("Spotlight", True), ("Trade", True),
                        ("Impulse", False), ("Prestige", False)):
        page = f'<script src="//cdn.shopify.com/x.js"></script><script>Shopify.theme = {{"name":"{theme}"}};</script>'
        assert kf.shopify_check(page, {}, "")["free_theme"] is free


def test_reviews_apps_motion_and_page_checks():
    dawn = kf.shopify_check(DAWN, {}, "https://velvet.test")
    assert dawn["reviews"] == "" and dawn["no_motion"] and dawn["static_banner"] and dawn["default_fonts"]
    assert dawn["third_party"] == 1 and dawn["third_party_hosts"] == ["googletagmanager.com"]
    assert dawn["images_no_size"] == 3 and dawn["meta_description"] and not dawn["heavy"]
    prestige = kf.shopify_check(PRESTIGE, {}, "https://crown.test")
    assert prestige["reviews"] == "Judge.me" and prestige["video"] and prestige["animation"]
    assert not prestige["no_motion"] and not prestige["default_fonts"]
    for marks, app in (('<div class="yotpo-main">', "Yotpo"), ('<script src="https://loox.io/w.js">', "Loox"),
                       ('<div data-oke-widget class="okendo">', "Okendo"), ('<div class="stamped-reviews">', "Stamped"),
                       ('<span class="spr-badge">', "Shopify Product Reviews")):
        assert kf.shopify_check(marks, {}, "")["reviews"] == app
    scroll = kf.shopify_check('<div class="scroll-trigger animate--slide-in">x</div>', {}, "")
    assert scroll["scroll_effects"] and not scroll["no_motion"]
    heavy = kf.shopify_check(DAWN + "<!--" + "x" * 600_000 + "-->", {}, "")
    assert heavy["heavy"] and heavy["page_kb"] > 500


def test_store_checks_bring_a_fast_shopify_score_down_with_plain_reasons():
    plain = kf.score_page("https://velvet.test", DAWN, 0.3, len(DAWN), True, YEAR)
    assert plain["score"] >= 90  # Shopify's CDN makes the ordinary audit look good
    a = kf.apply_store(plain, kf.shopify_check(DAWN, {}, "https://velvet.test"))
    names = [x["problem"] for x in a["problems"]]
    assert names[:3] == ["Shopify's free Dawn theme", "No movement or personality", "No customer reviews on the store"]
    assert "a static banner and default fonts" in a["problems"][1]["why"]
    assert a["score"] < 70 and a["lead_type"] == kf.STORE_LEAD and a["builder"] == "Shopify"
    again = kf.apply_store(a, a["shopify"])  # applying twice doesn't double the store problems
    assert [x["problem"] for x in again["problems"]] == names


def test_ranking_among_stores_free_theme_and_no_motion_then_no_reviews_then_heavy():
    def store(name, score=80, **checks):
        s = {"is_shopify": True, "free_theme": False, "no_motion": False, "reviews": "Judge.me", "heavy": False,
             **checks}
        return {"name": name, "website": f"https://{name}.test", "audit": {"grade": "good", "score": score,
                                                                          "shopify": s}}
    rows = [store("heavy", heavy=True), store("polished", 70), store("noreviews", reviews=""),
            store("dawnstill", 90, free_theme=True, no_motion=True),
            store("dawnmoving", free_theme=True), {"name": "weak", "website": "https://w.test",
                                                   "audit": {"grade": "weak", "score": 30}},
            {"name": "okay", "website": "https://o.test", "audit": {"grade": "needs work", "score": 60}},
            {"name": "unchecked", "website": "https://u.test"}]
    order = [r["name"] for r in sorted(rows, key=kf.rank_key)]
    assert order == ["weak", "dawnstill", "noreviews", "heavy", "dawnmoving", "polished", "okay", "unchecked"]


def test_store_kinds_search_shop_categories():
    assert kf.kind_key("shopify stores") == "stores" and kf.kind_key("online shop") == "stores"
    assert kf.kind_key("boutique") == "stores" and kf.kind_key("beauty shops") == "beauty shops"
    assert kf.kind_key("beauty") == "beauty" and kf.kind_key("wig shops") == "wigs"
    assert kf.kind_key("jewellers") == "jewellery" and kf.kind_key("gift shops") == "home and gifts"
    assert kf.kind_key("wine shops") == "food and drink" and kf.kind_key("gym wear") == "sports shops"
    assert kf.kind_key("pet shops") == "pet shops" and kf.kind_key("toy shops") == "kids shops"
    assert kf.kind_key("art shops") == "art shops" and kf.kind_key("clothes shops") == "fashion"
    assert kf.kind_key("barber shops") == "hairdressers" and kf.kind_key("coffee shop") == "cafes"
    q = kf.overpass_query(1, 2, 500, "stores")
    for tag in ("clothes", "wigs", "cosmetics", "jewelry", "gift", "deli", "sports", "pet", "toys", "art"):
        assert f'"shop"="{tag}"' in q
    assert all(k in kf.PLACES_WORDS for k in kf.KINDS)  # Google Places has words for every kind


# ---- finding and auditing stores ----------------------------------------------------------

def test_find_stores_makes_shopify_store_leads_ranked_by_store_checks(s):
    out = finder(s, action="find", town="Manchester", kind="online shop")
    assert any('"shop"="wigs"' in c for c in calls if isinstance(c, str))
    assert "3 run on Shopify" in out and "store makeover leads" in out
    rows = out.card["rows"]
    names = [r[1] for r in rows]
    assert names.index("Velvet Rose") < names.index("Crown Wigs")  # free theme, no motion first
    velvet = next(r for r in rows if r[1] == "Velvet Rose")
    assert velvet[2] == "boutique, Shopify store" and velvet[5] == "Shopify's free Dawn theme"
    saved = {p["name"]: p for p in st.rows_of(s, st.PROSPECTS)}
    assert saved["Velvet Rose"]["lead_type"] == "Shopify store" and "lead_type" not in saved["Wix Gifts"]
    assert saved["Paws Ltd"]["audit"]["shopify"]["via"] == "products.json"  # the backup signal
    assert not any(isinstance(c, httpx.Request) and c.url.host == "www.googleapis.com" for c in calls)  # no key


def test_pagespeed_mobile_score_only_with_a_key_sent_in_a_header(s, capsys):
    k = replace(s, pagespeed_key="speed-key")
    out = finder(k, action="audit", url="https://velvet.test")
    speed = [c for c in calls if isinstance(c, httpx.Request) and c.url.host == "www.googleapis.com"]
    assert len(speed) == 1 and "speed-key" not in str(speed[0].url) and speed[0].url.params["strategy"] == "mobile"
    assert "PageSpeed 31/100 on phones" in out and "speed-key" not in out and "speed-key" not in capsys.readouterr().out
    a = st.rows_of(s, st.PROSPECTS)[0]["audit"]
    assert a["shopify"]["pagespeed"] == 31 and "Slow on phones (Google PageSpeed 31/100)" in [
        x["problem"] for x in a["problems"]]
    report = (memory.root(s) / "Kinetic Web Designs" / "Audits" / "velvet.test.md").read_text(encoding="utf-8")
    assert "Shopify store checks" in report and "Copy of Dawn (one of Shopify's free themes)" in report
    assert "Google PageSpeed on phones: 31/100" in report
    bad = replace(s, pagespeed_key="wrong")  # a refused key is skipped silently
    assert "PageSpeed" not in finder(bad, action="audit", url="https://crown.test")


# ---- store makeover outreach ----------------------------------------------------------------

def test_store_makeover_opener_mockup_and_channel_rules(s):
    finder(s, action="find", town="Manchester", kind="shopify")
    sales(s, action="my_details", owner="Lee")
    out = sales(s, action="outreach", client="Velvet Rose", channel="email")
    body = out.card["text"]
    opener = ("Your store uses Shopify's free default theme, so it looks like thousands of others: no movement, "
              "nothing that feels like Velvet Rose.")
    assert body.startswith(f"Subject: I made this for Velvet Rose\n\nHi there,\n\n{opener} So I made you this: a free "
                           "store makeover for Velvet Rose, a new home page in your brand with movement and personality.")
    assert "(Velvet Rose store makeover mock-up.html)" in body and f"\n\n{st.PREVIEW}\n\n" in body
    assert f"A Shopify store redesign is £595, and you pay {TERMS}." in body and "pay Shopify directly" in body
    assert "Thanks,\nAlfred, Kinetic Web Designs" in body and "Lee" not in body
    assert "instalment" not in body.lower() and "klarna" not in body.lower()
    assert "free store makeover mock-up: Kinetic Web Designs/Mockups/Velvet Rose/Velvet Rose store makeover" in out
    html = (memory.root(s) / "Kinetic Web Designs" / "Mockups" / "Velvet Rose" / "index.html").read_text(encoding="utf-8")
    for bit in ("@keyframes", "animation-timeline:view()", 'class="product reveal"', "Loved by our customers",
                "prefers-reduced-motion", "Copy of Dawn theme", 'href="tel:01610000002"'):
        assert bit in html
    assert "<script" not in html and "Velvet Rose" in html
    # channel rules still apply: a UK sole trader gets a phone script and a DM, a Ltd gets an email first
    plan = sales(s, action="outreach", client="Crown Wigs").card["text"]
    assert plan.startswith("Phone script for Crown Wigs") and "Instagram DM:" in plan
    dm = plan.split("Instagram DM:\n\n")[1].split("\n\nIf you'd rather")[0]
    assert "free store makeover mock-up" in dm and len(dm) <= ks.DM_LIMIT and "£595" in dm
    assert sales(s, action="outreach", client="Paws Ltd").card["text"].startswith("Subject: I made this for Paws Ltd")


def test_store_problem_lines_in_plain_words():
    def lead(**checks):
        shop = {"is_shopify": True, "free_theme": False, "no_motion": False, "reviews": "Loox", "heavy": False,
                "base_theme": "", **checks}
        return {"name": "Glow", "website": "https://glow.test", "audit": {"grade": "good", "score": 80,
                                                                          "problems": [], "shopify": shop}}
    assert kf.biggest_problem(lead(free_theme=True, base_theme="Sense"))["line"] == \
        "Your store uses Shopify's free Sense theme, so it looks like thousands of others: nothing that feels like Glow."
    assert "no movement and no personality" in kf.biggest_problem(lead(no_motion=True))["line"]
    assert "shows no customer reviews" in kf.biggest_problem(lead(reviews=""))["line"]
    assert "Google gives it 22 out of 100" in kf.biggest_problem(lead(pagespeed=22))["line"]
    assert "heavy home page" in kf.biggest_problem(lead(heavy=True))["line"]


# ---- prices ---------------------------------------------------------------------------------

def test_shopify_prices_quotes_care_and_founding_offer(s):
    out = sales(s, action="prices")
    assert "Shopify store redesign £595" in out and "Shopify store setup £995" in out
    assert "keep paying Shopify directly" in out
    sales(s, action="quote", client="Velvet", package="shopify_redesign", founding=True, existing_website=True)
    q = st.rows_of(s, st.QUOTES)[0]
    assert q["total"] == 495 and q["founding_discount"] == 100 and q["rebuild_discount"] == 0 and q["care"] == 25
    html = (memory.root(s) / "Kinetic Web Designs" / "Clients" / "Velvet" / "Quote Q-0001.html").read_text(encoding="utf-8")
    assert "Shopify store redesign" in html and "keep paying Shopify directly for your Shopify plan" in html
    assert "half when we start building, half once everything" in html and "Klarna" not in html
    out = sales(s, action="quote", client="New Brand", package="Shopify store setup")
    assert "£995" in out and "keep paying Shopify directly" in out and st.rows_of(s, st.QUOTES)[1]["care"] == 30
    sales(s, action="set_price", item="shopify store redesign", price=650)
    sales(s, action="set_price", item="care_plan", package="shopify_setup", price=35)
    p = ks.prices(s)
    assert p["packages"]["shopify_redesign"]["price"] == 650 and ks.care_price(p, "shopify_setup") == 35
    assert p["packages"]["shopify_setup"]["price"] == 995 and ks.care_price(p, "business") == 25
    assert world.payment_terms(50) == TERMS


def test_store_lead_goes_into_the_pipeline_as_a_shopify_redesign(s):
    finder(s, action="find", town="Manchester", kind="shopify")
    out = finder(s, action="add_lead", business="Velvet Rose")
    assert "£595" in out


# ---- trade of the week ------------------------------------------------------------------------

def test_trade_of_the_week_takes_shopify_stores_or_a_store_kind(s):
    out = reach(s, action="trade_of_week", trade="shopify stores")
    week = st.trade_of_week(s)
    assert week["kind"] == "stores" and week["trade"] == "shop" and "store makeover" in out
    finder(s, action="find", town="Manchester")  # no kind: this week's stores
    assert any('"shop"="clothes"' in c for c in calls if isinstance(c, str))
    assert ks.next_weekly_lead(s) == str(st.find_prospect(st.rows_of(s, st.PROSPECTS), "Velvet Rose")["id"])
    reach(s, action="trade_of_week", trade="beauty shops")
    assert st.trade_of_week(s)["kind"] == "beauty shops" and st.trade_of_week(s)["trade"] == "beauty"
