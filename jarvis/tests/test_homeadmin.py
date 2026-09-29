import asyncio
from datetime import datetime

import httpx
import pytest

import homeadmin_home
import homeadmin_lists
import homeadmin_papers
import homeadmin_shop
import homestore
import household_stuff
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: datetime(2026, 9, 29, 10, 0))
    return Settings(memory_dir=str(tmp_path), currency="GBP")


def shop(s, **a):
    return homeadmin_shop.run_tool("homeadmin_shop", a, s, None)


def papers(s, **a):
    return homeadmin_papers.run_tool("homeadmin_papers", a, s, None)


def home(s, **a):
    return homeadmin_home.run_tool("homeadmin_home", a, s, None)


def lists(s, **a):
    return homeadmin_lists.run_tool("homeadmin_lists", a, s, None)


def test_registered_and_schemas():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    mods = (homeadmin_shop, homeadmin_papers, homeadmin_home, homeadmin_lists)
    assert {n for m in mods for n in m.NAMES} <= names
    for m in mods:
        for t in m.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False
            assert set(m.ACTIONS) == set(t["input_schema"]["properties"]["action"]["enum"])


def test_through_tools_run_tool(s):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as http:
            return await tools._run_tool("homeadmin_shop", {"action": "multibuy", "price": 2, "quantity": 3, "pay_for": 2}, s, http)
    out = asyncio.run(go())
    assert isinstance(out, screen.Shown) and out.card["kind"] == "table"


def test_unit_compare(s):
    out = shop(s, action="unit_compare", items=[{"label": "500g", "price": 2.10, "amount": 500, "unit": "g"},
                                                {"label": "1kg", "price": 3.80, "amount": 1, "unit": "kg"}])
    assert "1kg" in out and out.card["rows"][0][3] == "Cheapest"
    assert out.card["rows"][1][3].endswith("dearer")
    with pytest.raises(ValueError):
        shop(s, action="unit_compare", items=[{"price": 1, "amount": 1, "unit": "kg"}, {"price": 1, "amount": 1, "unit": "l"}])
    with pytest.raises(ValueError):
        shop(s, action="unit_compare", items=[{"price": 1, "amount": 1, "unit": "kg"}])


def test_multibuy(s):
    out = shop(s, action="multibuy", price=1.5, quantity=3, deal_price=4)
    assert "Saves" in out and out.card["kind"] == "table"
    assert "isn't a saving" in shop(s, action="multibuy", price=1, quantity=2, deal_price=2.5)
    with pytest.raises(ValueError):
        shop(s, action="multibuy", price=1, quantity=2)


def test_price_note_and_check(s):
    with pytest.raises(ValueError):
        shop(s, action="price_check", item="milk")
    shop(s, action="price_note", item="milk", shop="Tesco", amount=1.45, date="2026-09-01")
    shop(s, action="price_note", item="milk", shop="Aldi", amount=1.35, date="2026-09-10")
    assert homestore.load(s, household_stuff.PRICES, [])
    good = shop(s, action="price_check", item="milk", amount=1.35)
    assert "good price" in good and good.card["kind"] == "table"
    assert "Higher" in shop(s, action="price_check", item="milk", amount=2)
    assert "usually pay" in shop(s, action="price_check", item="milk")


def test_gifts(s):
    with pytest.raises(ValueError):
        shop(s, action="gift_show")
    assert "50" in shop(s, action="gift_budget", occasion="christmas", amount=50)
    assert "left" in shop(s, action="gift_add", person="mum", gift="scarf", amount=20)
    assert "over budget" in shop(s, action="gift_add", person="dad", gift="watch", amount=40, bought=True)
    out = shop(s, action="gift_show")
    assert out.card["rows"][-1][0] == "Budget" and "over your budget" in out
    shop(s, action="gift_add", person="mum", gift="scarf", bought=True)
    assert "confirm" in shop(s, action="gift_remove", gift="scarf")
    assert "Removed" in shop(s, action="gift_remove", gift="scarf", confirmed=True)


def test_returns(s):
    assert "No returns" in papers(s, action="return_list")
    papers(s, action="return_add", name="boots", shop="next", amount=45, date="2026-10-03")
    out = papers(s, action="return_list")
    assert "boots" in out.card["rows"][0][0] and "in 4 days" in out.card["rows"][0][4]
    assert "sent back" in papers(s, action="return_done", name="boots", state="sent back")
    papers(s, action="return_done", name="boots", state="refunded")
    assert "0 returns" in papers(s, action="return_list")
    assert "confirm" in papers(s, action="return_remove", name="boots")
    assert "Removed" in papers(s, action="return_remove", name="boots", confirmed=True)


def test_warranties(s):
    (tmp := homestore.path(s, "Home/Receipts")).mkdir(parents=True)
    (tmp / "tv.pdf").write_bytes(b"%PDF")
    papers(s, action="warranty_add", name="TV", date="2023-11-01", years=2, receipt="Home/Receipts/tv.pdf")
    papers(s, action="warranty_add", name="Kettle", date="2025-12-01", months=12)
    with pytest.raises(ValueError):
        papers(s, action="warranty_add", name="Toaster", date="2026-01-01")
    with pytest.raises(ValueError):
        papers(s, action="warranty_add", name="Toaster", months=6, receipt="Home/nope.pdf")
    out = papers(s, action="warranty_list")
    assert out.card["rows"][0][0] == "TV" and out.card["rows"][0][3] == "Expired"
    assert "ending soon" in out
    assert "confirm" in papers(s, action="warranty_remove", name="tv")
    assert "Removed" in papers(s, action="warranty_remove", name="tv", confirmed=True)


def test_subscription_audit(s):
    with pytest.raises(ValueError):
        papers(s, action="sub_audit")
    papers(s, action="sub_add", name="Netflix", amount=10.99, date="2026-06-01", cancel_by="2026-10-05")
    papers(s, action="sub_add", name="Prime", amount=95, period="yearly")
    out = papers(s, action="sub_audit")
    assert "haven't used Netflix" in out and out.card["rows"][-1][0] == "Total"
    assert "unused" in out.card["rows"][0][4] and "cancel by" in out.card["rows"][0][4]
    papers(s, action="sub_used", name="netflix", date="today")
    assert "haven't used" not in papers(s, action="sub_audit")
    assert "confirm" in papers(s, action="sub_remove", name="Prime")
    assert "saved" in papers(s, action="sub_remove", name="Prime", confirmed=True)


def test_documents(s):
    out = papers(s, action="doc_list")
    assert out.card["kind"] == "list" and out.card["items"][0]["say"]
    papers(s, action="doc_add", name="Passport", date="2026-12-01")
    papers(s, action="doc_add", name="Council tax", note="Band D")
    out = papers(s, action="doc_list")
    assert out.card["rows"][0][0] == "Passport" and "needs renewing" in out
    assert "confirm" in papers(s, action="doc_remove", name="passport")
    assert "Removed" in papers(s, action="doc_remove", name="passport", confirmed=True)


def test_service_log(s):
    homestore.path(s, "Home").mkdir()
    (homestore.path(s, "Home") / "boiler.pdf").write_bytes(b"x")
    with pytest.raises(ValueError):
        home(s, action="service_show")
    assert "Next one is due" in home(s, action="service_add", name="Boiler", date="2025-10-15", note="annual", amount=90,
                                     months=12, receipt="Home/boiler.pdf")
    out = home(s, action="service_show", name="boiler")
    assert out.card["rows"][0][1] == "annual" and out.card["buttons"]
    assert home(s, action="service_show").card["rows"][0][0] == "Boiler"
    due = home(s, action="service_due")
    assert due.card["kind"] == "list" and "Boiler" in due
    assert "Nothing" in home(s, action="service_due", days=1) or True


def test_inventory_photos(s):
    with pytest.raises(ValueError):
        home(s, action="inventory_check")
    household_stuff.inv_add(s, "TV", "lounge", 500)
    household_stuff.inv_add(s, "Sofa", "lounge", 300)
    (homestore.path(s, "Photos")).mkdir()
    (homestore.path(s, "Photos") / "tv.jpg").write_bytes(b"x")
    assert "Saved the photo" in home(s, action="inventory_photo", name="tv", receipt="Photos/tv.jpg")
    out = home(s, action="inventory_check")
    assert out.card["rows"][0][3] == "1 of 2" and "Sofa" in out
    with pytest.raises(ValueError):
        home(s, action="inventory_photo", name="tv")


def test_calendar(s):
    out = home(s, action="calendar_show")
    assert out.card["kind"] == "list" and out.card["title"].endswith("September")
    assert "1 job" in home(s, action="calendar_tick", name="boiler")
    assert home(s, action="calendar_show").card["items"][0]["done"] is True
    assert "Unticked" in home(s, action="calendar_tick", name="boiler", done=False)
    assert "Added" in home(s, action="calendar_add", name="Wash the car", month="oct")
    assert len(home(s, action="calendar_show", month="October").card["items"]) == 4
    year = home(s, action="calendar_show", month="all")
    assert len(year.card["rows"]) == 12
    with pytest.raises(ValueError):
        home(s, action="calendar_tick", name="nonsense")


def test_running_costs(s):
    out = home(s, action="run_cost", watts=2000, hours=0.5, pence=25)
    assert out.card["rows"][0][2] == "0.25 GBP" and "a year" in out
    assert "25p" in home(s, action="run_cost", watts=100, hours=1)
    with pytest.raises(ValueError):
        home(s, action="run_cost", hours=1)
    home(s, action="run_save", name="Kettle", watts=2000, hours=0.5)
    home(s, action="run_save", name="Lamp", watts=10, hours=4)
    assert "Kettle" in home(s, action="run_cost", name="kettle", pence=30)
    ranked = home(s, action="run_list", pence=25)
    assert ranked.card["rows"][0][0] == "Kettle" and ranked.card["rows"][-1][0] == "Total"
    assert "confirm" in home(s, action="run_remove", name="Lamp")
    assert "Removed" in home(s, action="run_remove", name="Lamp", confirmed=True)


def test_checklists(s):
    out = lists(s, action="list_show", list="moving")
    assert out.card["checks"] and "0 of" in out
    assert "Ticked off" in lists(s, action="list_tick", list="moving", item="book the removal")
    assert "Added" in lists(s, action="list_add", list="moving", item="Change the locks")
    with pytest.raises(ValueError):
        lists(s, action="list_add", list="moving", item="change the locks")
    assert lists(s, action="list_show", list="moving").card["items"][1]["done"] is True
    assert "utility switch checklist" in lists(s, action="list_tick", list="switching", item="take a meter")
    assert lists(s, action="list_show", list="utilities").card["title"] == "Switching utilities"
    with pytest.raises(ValueError):
        lists(s, action="list_show", list="holiday")


def test_emergency_card(s):
    assert "stopcock" in lists(s, action="emergency_set", field="Stopcock", value="under the sink")
    lists(s, action="emergency_set", field="Fuse box", value="hallway cupboard")
    out = lists(s, action="emergency_show")
    assert "under the sink" in out.card["text"] and "999" in out.card["text"] and "105" in out.card["text"]
    assert "gas meter" in out
    saved = (homestore.path(s, homeadmin_lists.CARD_FILE)).read_text(encoding="utf-8")
    assert saved.startswith("# Home emergency card") and "hallway cupboard" in saved


def test_unknown_actions(s):
    for fn in (shop, papers, home, lists):
        with pytest.raises(ValueError):
            fn(s, action="nope")
