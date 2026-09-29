import asyncio
import json
from datetime import timedelta

import pytest

import memory
import screen
import sellercalc_fees
import sellercalc_guide
import sellercalc_listing
import sellercalc_stock
import sellercalc_store as sc
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def fees(s, action, **a):
    return sellercalc_fees.run_tool("sellercalc_fees", {"action": action, **a}, s)


def stock(s, action, **a):
    return sellercalc_stock.run_tool("sellercalc_stock", {"action": action, **a}, s)


def listing(s, action, **a):
    return sellercalc_listing.run_tool("sellercalc_listing", {"action": action, **a}, s)


def guide(s, action, **a):
    return sellercalc_guide.run_tool("sellercalc_guide", {"action": action, **a}, s)


def kind(shown):
    assert isinstance(shown, screen.Shown)
    return shown.card["kind"]


def rows_of(shown):
    return dict(shown.card["data"]["rows"])


def test_registered_and_through_tools(s):
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"sellercalc_fees", "sellercalc_stock", "sellercalc_listing", "sellercalc_guide"} <= names
    assert {sc.RESULT, sc.COMPARE, sc.FEES, sc.BARS, sc.GUIDE} <= screen.EXTRA_KINDS
    out = asyncio.run(tools._run_tool("sellercalc_fees", {"action": "profit", "platform": "etsy", "price": 20, "cost": 5}, s, None))
    assert kind(out) == sc.RESULT


def test_every_action_has_a_handler_and_schema():
    for mod in (sellercalc_fees, sellercalc_stock, sellercalc_listing, sellercalc_guide):
        tool = mod.tool_definitions()[0]
        assert tool["input_schema"]["additionalProperties"] is False
        assert tool["input_schema"]["properties"]["action"]["enum"] == mod.ACTIONS
    total = sum(len(m.ACTIONS) for m in (sellercalc_fees, sellercalc_stock, sellercalc_listing, sellercalc_guide))
    assert total >= 50


def test_fee_maths():
    etsy = sc.PLATFORMS["etsy"]
    assert sc.fee_of(etsy, 20, 3) == round(23 * 0.105 + 0.36, 2)
    ebay = sc.PLATFORMS["ebay_business"]
    assert sc.fee_of(ebay, 8) == round(8 * 0.128 + 0.10, 2)
    assert sc.fee_of(ebay, 20) == round(20 * 0.128 + 0.30, 2)
    assert sc.fee_of(sc.PLATFORMS["vinted"], 30) == 0
    assert sc.fee_of(sc.PLATFORMS["facebook_shipped"], 2) == 0.80
    assert sc.FEES_CHECKED == "2026-09"


def test_solver_hits_target():
    for key, rate in sc.PLATFORMS.items():
        price = sc.solve_price(rate, 5.0, None, cost=4.0, ship_charged=3.0, ship_cost=3.2)
        assert sc.profit_on(rate, price, 4.0, 3.0, 3.2)["net"] >= 5.0
        assert sc.profit_on(rate, price - 0.01, 4.0, 3.0, 3.2)["net"] < 5.0, key


def test_fee_table_and_override(s):
    shown = fees(s, "fee_table")
    assert kind(shown) == sc.FEES and shown.card["data"]["checked"] == sc.FEES_CHECKED
    assert len(shown.card["data"]["rows"]) == len(sc.PLATFORMS)
    assert kind(fees(s, "fee_table", platform="vinted")) == sc.RESULT
    before = fees(s, "profit", platform="etsy", price=20, cost=5)
    assert "saved" in fees(s, "set_rate", platform="etsy", pct=5, fixed=0.1).lower()
    after = fees(s, "profit", platform="etsy", price=20, cost=5)
    assert after.card["data"]["headline"] != before.card["data"]["headline"]
    assert json.loads((memory.root(s) / sc.SETTINGS).read_text())["rates"]["etsy"]["pct"] == 5
    assert fees(s, "fee_table").card["data"]["rows"][0]["mine"] == ["fixed", "pct"]
    assert "back" in fees(s, "reset_rate", platform="etsy")
    assert fees(s, "profit", platform="etsy", price=20, cost=5).card["data"]["headline"] == before.card["data"]["headline"]
    with pytest.raises(ValueError):
        fees(s, "set_rate", platform="etsy")
    with pytest.raises(ValueError):
        fees(s, "profit", platform="nowhere", price=5)


def test_profit_on_platforms(s):
    v = fees(s, "profit", platform="vinted", price=20, cost=5, ship_cost=3)
    assert v.card["data"]["headline"] == "£15"
    assert any("buyer" in n for n in v.card["data"]["notes"])
    loss = fees(s, "profit", platform="etsy", price=5, cost=5)
    assert loss.card["data"]["headline"].startswith("£-") or loss.card["data"]["headline"].startswith("-")
    assert kind(fees(s, "profit", platform="ebay business", price=30, cost=10, ship_charged=3.5, ship_cost=3.2, extra_pct=2))
    with pytest.raises(ValueError):
        fees(s, "profit", platform="etsy")


def test_compare_pops_up_best_first(s):
    shown = fees(s, "compare", price=25, cost=8, ship_charged=3, ship_cost=3)
    assert kind(shown) == sc.COMPARE
    rows = shown.card["data"]["rows"]
    assert rows[0]["best"] and rows[0]["net"] >= rows[-1]["net"]
    assert {r["key"] for r in rows} == set(sc.PLATFORMS)
    assert all(r["say"] for r in rows)
    few = fees(s, "compare", price=25, platforms=["etsy", "vinted"])
    assert len(few.card["data"]["rows"]) == 2


def test_target_and_floor_price(s):
    one = fees(s, "target_price", platform="etsy", cost=6, target_profit=5, ship_charged=3, ship_cost=3)
    assert kind(one) == sc.RESULT
    price = float(one.card["data"]["headline"].lstrip("£"))
    assert sc.profit_on(sc.PLATFORMS["etsy"], price, 6, 3, 3)["net"] >= 5
    every = fees(s, "target_price", cost=6, target_margin_pct=30)
    assert kind(every) == "table" and len(every.card["rows"]) == len(sc.PLATFORMS)
    floor = fees(s, "floor_price", platform="depop", cost=10)
    assert float(floor.card["data"]["headline"].lstrip("£")) > 10
    with pytest.raises(ValueError):
        fees(s, "target_price", platform="etsy", cost=6)


def test_offer_discount_bundle(s):
    offer = fees(s, "offer_check", platform="depop", price=30, offer=20, cost=10, target_profit=3)
    assert kind(offer) == sc.RESULT and "counter" in offer or "works" in offer
    assert kind(fees(s, "discount", platform="etsy", price=25, discount_pct=20, cost=8, ship_cost=3))
    dead = fees(s, "discount", platform="etsy", price=10, discount_pct=50, cost=6)
    assert "no profit" in dead
    b = fees(s, "bundle", platform="ebay business", items=[{"price": 10, "cost": 2}, {"price": 12, "cost": 3}], bundle_discount_pct=10,
             ship_cost=3, ship_charged=3)
    assert kind(b) == sc.RESULT and "Profit selling separately" in rows_of(b)
    with pytest.raises(ValueError):
        fees(s, "bundle", platform="etsy", items=[{"price": 10}])


def test_vinted_fba_pod_shop(s):
    v = fees(s, "vinted_explain", price=20, cost=4)
    assert rows_of(v)["Vinted takes from you"] == "£0" and rows_of(v)["You receive"] == "£20"
    assert "pays no fee" in v
    amazon = fees(s, "amazon_fba_fbm", price=20, cost=5, ship_cost=3, size="small")
    assert kind(amazon) == sc.RESULT and "FBA profit" in rows_of(amazon)
    mark = fees(s, "pod_price", base_cost=12, markup_pct=25)
    assert mark.card["data"]["headline"] == "£3"
    own = fees(s, "pod_price", base_cost=12, printer_shipping=3, target_profit=4, ship_charged=3)
    assert float(own.card["data"]["headline"].lstrip("£")) > 12
    shop = fees(s, "shop_monthly", price=30, cost=10, ship_cost=3, orders=20, plan_cost=25)
    assert "Orders to cover the plan" in rows_of(shop)


def test_postage_table_edit_and_suggest(s):
    table = fees(s, "postage_table")
    assert kind(table) == "table" and "approximate" in table.card["text"].lower()
    suggest = fees(s, "postage_suggest", weight_g=600)
    assert suggest.card["data"]["sub"].startswith("Royal Mail Large Letter")
    heavy = fees(s, "postage_suggest", weight_g=1800, longest_cm=40)
    assert "parcel" in heavy.card["data"]["sub"].lower()
    assert "Saved" in fees(s, "postage_set", service="rm_large_letter", price=2.5)
    assert fees(s, "postage_suggest", weight_g=600).card["data"]["headline"] != "£1.75"
    assert "Saved" in fees(s, "postage_set", service="DPD tiny", price=4, max_g=500)
    with pytest.raises(ValueError):
        fees(s, "postage_set", service="Something new")
    with pytest.raises(ValueError):
        fees(s, "postage_suggest", weight_g=39000, longest_cm=250)
    assert "confirm" in fees(s, "postage_reset")
    assert "back" in fees(s, "postage_reset", confirmed=True)
    assert fees(s, "postage_suggest", weight_g=600).card["data"]["headline"] == "£1.75"


def test_stock_lifecycle(s):
    assert "Added item 1" in stock(s, "add_item", name="Levi jacket", bought_for=6, source="charity shop", category="Clothes")
    stock(s, "add_item", name="Kettle", bought_for=3, category="home", bought_date="2026-01-01")
    listed = stock(s, "list_item", item="Levi jacket", platform="vinted", price=25)
    assert "Listed" in listed and "£19" in listed
    sold = stock(s, "sell_item", item="1", sold_for=25, platform="ebay business", postage=3, postage_charged=3.5)
    assert "profit" in sold and "fee table" in sold
    item = sc.items(s)[0]
    assert item["status"] == "sold" and item["fees"] > 0
    with pytest.raises(ValueError):
        stock(s, "sell_item", item="1", sold_for=20)
    assert kind(stock(s, "item_detail", item="Levi jacket")) == sc.RESULT
    assert "Updated" in stock(s, "update_item", item="Kettle", category="kitchen", new_name="Old kettle", bought_for=4)
    table = stock(s, "show_items")
    assert kind(table) == "table" and len(table.card["rows"]) == 2
    assert len(stock(s, "show_items", status="in stock").card["rows"]) == 1
    with pytest.raises(ValueError):
        stock(s, "show_items", query="zzz")
    assert "confirm" in stock(s, "remove_item", item="Old kettle")
    assert len(sc.items(s)) == 2
    assert "Removed" in stock(s, "remove_item", item="Old kettle", confirmed=True)
    assert len(sc.items(s)) == 1
    with pytest.raises(ValueError):
        stock(s, "list_item", item="Levi jacket", platform="etsy", price=5)


def fill(s):
    today = sc.today()
    d = lambda n: (today - timedelta(days=n)).isoformat()  # noqa: E731
    stock(s, "add_item", name="Coat", bought_for=5, category="clothes", source="car boot", bought_date=d(100))
    stock(s, "add_item", name="Mug", bought_for=1, category="home", bought_date=d(70))
    stock(s, "add_item", name="Book", bought_for=2, category="books", bought_date=d(10))
    stock(s, "add_item", name="Dress", bought_for=4, category="clothes", bought_date=d(40))
    stock(s, "list_item", item="Mug", platform="vinted", price=8, date=d(60))
    stock(s, "list_item", item="Coat", platform="ebay", price=30, date=d(90))
    stock(s, "list_item", item="Dress", platform="vinted", price=20, date=d(30))
    stock(s, "sell_item", item="Dress", sold_for=18, platform="vinted", postage=2.5, date=d(10))
    stock(s, "sell_item", item="Book", sold_for=7, platform="ebay", postage=2, fees=0.5, date=d(3))


def test_reports(s):
    with pytest.raises(ValueError):
        stock(s, "summary")
    fill(s)
    dress = next(i for i in sc.items(s) if i["name"] == "Dress")
    assert sc.item_profit(dress) == 18 - 2.5 - 4 and sc.days_to_sell(dress) == 20
    value = stock(s, "stock_value")
    assert kind(value) == sc.BARS and "2 unsold" in value and "£6" in value
    age = stock(s, "ageing")
    assert kind(age) == sc.BARS and age.card["data"]["rows"][3]["value"] == "1 items"
    assert "over 90 days" in age
    through = stock(s, "sell_through")
    assert "50%" in through and kind(through) == sc.BARS
    assert kind(stock(s, "sell_through", days=30)) == sc.BARS
    best = stock(s, "best_categories")
    assert kind(best) == sc.BARS and best.card["data"]["rows"][0]["label"] in ("clothes", "books")
    chart = stock(s, "monthly_profit", months=3)
    assert kind(chart) == "chart" and len(chart.card["chart"]["values"]) == 3
    assert sum(chart.card["chart"]["values"]) == pytest.approx(sum(map(sc.item_profit, [i for i in sc.items(s) if sc.is_sold(i)])))
    summ = stock(s, "summary")
    assert kind(summ) == sc.RESULT and rows_of(summ)["Items sold"] == "2"
    slow = stock(s, "slow_movers", days=60)
    assert kind(slow) == "list" and len(slow.card["items"]) == 2 and slow.card["items"][0]["say"]
    assert "Nothing" in stock(s, "slow_movers", days=500)
    plat = stock(s, "platform_results")
    assert kind(plat) == "table" and len(plat.card["rows"]) == 2
    assert kind(stock(s, "speed")) == sc.BARS and kind(stock(s, "speed", by="category")) == sc.BARS


def test_export_and_returns(s):
    fill(s)
    out = stock(s, "export_csv")
    assert kind(out) == "file" and out.card["name"].endswith(".csv")
    assert "profit" in (memory.root(s) / "Selling" / out.card["name"]).read_text()
    with pytest.raises(ValueError):
        stock(s, "returns_list")
    assert "Logged return 1" in stock(s, "log_return", item="Dress", reason="too small", refund=18, postage=2.5)
    stock(s, "log_return", item="a gift", refund=5)
    table = stock(s, "returns_list")
    assert kind(table) == "table" and len(table.card["rows"]) == 2 and "%" in table
    assert "Closed" in stock(s, "resolve_return", return_id="1", restocked=True)
    assert "closed, restocked" in stock(s, "returns_list").card["rows"][1][6]
    with pytest.raises(ValueError):
        stock(s, "resolve_return", return_id="99")


def test_listing_helpers(s):
    t = listing(s, "title", item="denim jacket", brand="Levi's", colour="blue", size="M", condition="excellent", platform="Vinted",
                keywords=["oversized", "90s"])
    assert kind(t) == "list" and t.card["items"][0]["say"].startswith("Save a listing draft")
    ebay = listing(s, "title", item="denim jacket " * 5, brand="Levi's", colour="blue", size="M", keywords=["x" * 25] * 6, platform="ebay")
    assert all(len(i["label"].split(": ", 1)[1]) <= 80 for i in ebay.card["items"])
    kw = listing(s, "keywords", item="mug", colour="blue", material="ceramic", platform="etsy")
    assert all(len(i["label"]) <= 20 for i in kw.card["items"]) and len(kw.card["items"]) <= 13
    assert listing(s, "keywords", item="mug", platform="depop").card["items"][0]["label"].startswith("#")
    d = listing(s, "description", item="jacket", brand="Levi's", size="M", flaws="small mark on cuff")
    assert kind(d) == "text" and "small mark on cuff" in d.card["text"]
    assert "add any marks" in listing(s, "description", item="jacket").card["text"]
    assert kind(listing(s, "photo_checklist", item="shirt")) == "list"
    for plat in ("etsy", "ebay", "vinted", "depop", "facebook", "amazon", "own shop"):
        assert kind(listing(s, "listing_checklist", platform=plat)) == "list"
    assert kind(listing(s, "condition_guide")) == sc.GUIDE and kind(listing(s, "packing_checklist")) == "list"
    assert kind(listing(s, "price_research")) == sc.GUIDE
    r = listing(s, "price_research", prices=[12, 14, 16])
    assert r.card["data"]["headline"] == "£15.50"


def test_drafts(s):
    assert "Saved listing draft 1" in listing(s, "save_draft", title="Levi jacket size M", platform="vinted", price=20, text="lovely")
    assert kind(listing(s, "drafts")) == "table"
    assert "confirm" in listing(s, "delete_draft", draft_id="1")
    assert "Deleted" in listing(s, "delete_draft", draft_id="1", confirmed=True)
    with pytest.raises(ValueError):
        listing(s, "drafts")


def test_guides(s):
    h = guide(s, "hmrc_rules")
    assert kind(h) == sc.GUIDE and "30" in json.dumps(h.card["data"]) and "1,700" in json.dumps(h.card["data"])
    assert "GOV.UK" in h.card["data"]["note"]
    assert kind(guide(s, "sourcing_tips", kind="car boot")) == sc.GUIDE
    assert "Charity Shop" in json.dumps(guide(s, "sourcing_tips", kind="charity").card["data"])
    for a in ("seller_scams", "records_checklist", "returns_rules", "glossary"):
        assert isinstance(guide(s, a), screen.Shown)
    assert kind(guide(s, "platform_guide", platform="vinted")) == sc.GUIDE
    assert kind(guide(s, "platform_guide", platform="shopify")) == sc.GUIDE
    assert "Margin" in json.dumps(guide(s, "glossary", term="margin").card["data"])
    assert kind(guide(s, "seasonal")) == sc.GUIDE and kind(guide(s, "seasonal", month=12)) == sc.GUIDE


def test_sourcing_notes_and_max_buy(s):
    assert "Noted" in guide(s, "add_source", place="Sunday car boot", kind="car boot", spent=20, worth=60, count=8, note="arrive early")
    guide(s, "add_source", place="Oxfam", kind="charity shop", spent=10, worth=15)
    table = guide(s, "list_sources")
    assert kind(table) == "table" and len(table.card["rows"]) == 2 and "Sunday car boot" in table
    assert len(guide(s, "list_sources", place="oxfam").card["rows"]) == 1
    assert "confirm" in guide(s, "remove_source", source_id="1")
    assert "Removed" in guide(s, "remove_source", source_id="1", confirmed=True)
    mx = guide(s, "max_buy", platform="vinted", price=30, target_profit=10)
    assert mx.card["data"]["headline"] == "£20"
    assert "Skip" in guide(s, "max_buy", platform="etsy", price=5, target_profit=10, ship_cost=3)
    assert kind(guide(s, "max_buy", platform="depop", price=40, target_margin_pct=40)) == sc.RESULT


def test_bad_actions(s):
    for mod, name in ((sellercalc_fees, "sellercalc_fees"), (sellercalc_stock, "sellercalc_stock"),
                      (sellercalc_listing, "sellercalc_listing"), (sellercalc_guide, "sellercalc_guide")):
        with pytest.raises(ValueError):
            mod.run_tool(name, {"action": "nope"}, s)
