import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path

import pytest

import homestore
import incomestreams_goals as ig
import incomestreams_insights as ii
import incomestreams_streams as ist
import incomestreams_tax as it
import screen
import tools
from config import Settings


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: datetime(2026, 9, 29, 12, 0))


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def run(mod, s, action, **a):
    return mod.run_tool("x", {"action": action, **a}, s, None)


def card(x):
    assert isinstance(x, screen.Shown) and x.card
    return x.card


@pytest.fixture
def filled(s):
    run(ist, s, "stream_add", name="TikTok fund", type="active")
    run(ist, s, "stream_add", name="Affiliate", type="mixed")
    run(ist, s, "stream_add", name="Spare room", type="passive", tax_kind="property")
    for month, tik, aff, room in [("2026-04", 100, 20, 300), ("2026-05", 120, 30, 300), ("2026-06", 150, 40, 300),
                                  ("2026-07", 200, 50, 300), ("2026-08", 300, 60, 300), ("2026-09", 400, 80, 300)]:
        run(ist, s, "income_log", stream="TikTok fund", amount=tik, month=month, costs=10)
        run(ist, s, "income_log", stream="Affiliate", amount=aff, month=month)
        run(ist, s, "income_log", stream="Spare room", amount=room, month=month)
    return s


# ---- Streams ----------------------------------------------------------------------------------------

def test_stream_add_list_show_edit_status(s):
    assert "Added" in run(ist, s, "stream_add", name="Etsy prints", type="passive-ish")
    with pytest.raises(ValueError):
        run(ist, s, "stream_add", name="etsy prints")
    with pytest.raises(ValueError):
        run(ist, s, "stream_add", name="X", type="lucky")
    run(ist, s, "income_log", stream="etsy", amount=50)
    assert card(run(ist, s, "stream_list"))["kind"] == "table"
    show = run(ist, s, "stream_show", stream="Etsy")
    assert "£50" in show and card(show)["kind"] == "table"
    run(ist, s, "stream_edit", stream="Etsy prints", new_name="Etsy shop", type="mixed", note="hand made")
    assert "Etsy shop" in run(ist, s, "stream_show", stream=1)
    assert "paused" in run(ist, s, "stream_status", stream="Etsy shop", status="paused")
    with pytest.raises(ValueError):
        run(ist, s, "stream_status", stream="Etsy shop", status="dead")


def test_list_needs_streams_and_ideas(s):
    with pytest.raises(ValueError):
        run(ist, s, "stream_list")
    assert len(card(run(ist, s, "stream_ideas"))["rows"]) >= 8


def test_stream_remove_confirms_and_clears(filled):
    assert "confirm" in run(ist, filled, "stream_remove", stream="Affiliate")
    run(ist, filled, "stream_remove", stream="Affiliate", confirmed=True)
    with pytest.raises(ValueError):
        run(ist, filled, "stream_show", stream="Affiliate")
    saved = json.loads((Path(filled.memory_dir) / "incomestreams.json").read_text())
    assert not [e for e in saved["entries"] if e["stream"] == 2]


def test_income_log_edit_remove_list(s):
    run(ist, s, "stream_add", name="Freelance")
    out = run(ist, s, "income_log", stream="Freelance", amount="£1,250.50", costs=50, note="logo")
    assert "£1,250.50" in out
    with pytest.raises(ValueError):
        run(ist, s, "income_log", stream="Freelance", amount=-5)
    with pytest.raises(ValueError):
        run(ist, s, "income_log", stream="Freelance", amount=5, date="2026-12-01")
    listing = run(ist, s, "income_list", stream="Freelance", month="this month")
    assert card(listing)["rows"][0][2] == "Freelance"
    eid = int(out.split("entry ")[1].split(")")[0])
    run(ist, s, "income_edit", id=eid, amount=100)
    assert "confirm" in run(ist, s, "income_remove", id=eid)
    run(ist, s, "income_remove", id=eid, confirmed=True)
    assert "Nothing" in run(ist, s, "income_list")


def test_hours_log_and_list(filled):
    assert "3 hours" in run(ist, filled, "hours_log", stream="TikTok fund", hours=3, month="2026-09")
    with pytest.raises(ValueError):
        run(ist, filled, "hours_log", stream="TikTok fund", hours=0)
    table = card(run(ist, filled, "hours_list"))["rows"]
    assert table[0][1] == "3" and table[1][3] == "-"


def test_link_check_and_linked_stream(s, tmp_path):
    assert "no creator income" in run(ist, s, "link_check")
    (tmp_path / "creatorbiz-ledger.json").write_text(json.dumps([
        {"date": "2026-09-05", "kind": "income", "amount": 250, "category": "affiliate", "brand": "Amazon", "note": ""},
        {"date": "2026-09-06", "kind": "income", "amount": 500, "category": "brand deal", "brand": "Glow", "note": ""},
        {"date": "2026-09-07", "kind": "expense", "amount": 40, "category": "equipment", "brand": "", "note": ""}]))
    (tmp_path / "digitalproducts.json").write_text(json.dumps({"sales": [{"date": "2026-09-10", "amount": 12}]}))
    assert card(run(ist, s, "link_check"))["kind"] == "table"
    run(ist, s, "stream_add", name="Affiliate", link="creatorbiz", link_category="affiliate", type="mixed")
    run(ist, s, "stream_add", name="Products", link="digitalproducts")
    with pytest.raises(ValueError):
        run(ist, s, "income_log", stream="Affiliate", amount=5)
    dash = card(run(ii, s, "dashboard"))
    assert {x["name"]: sum(x["values"]) for x in dash["data"]["streams"]} == {"Affiliate": 250, "Products": 12}
    with pytest.raises(ValueError):
        run(ist, s, "stream_add", name="Bad", link="paypal")


# ---- Insights ---------------------------------------------------------------------------------------

def test_dashboard(filled):
    out = run(ii, filled, "dashboard", months=6)
    c = card(out)
    assert c["kind"] == "incomestreams-dashboard" and "promise" in out
    assert len(c["data"]["months"]) == 6 and c["data"]["totals"][-1] == 780
    assert c["data"]["streams"][0]["name"] == "Spare room"


def test_dashboard_empty(s):
    run(ist, s, "stream_add", name="A")
    with pytest.raises(ValueError):
        run(ii, s, "dashboard")


def test_month_table_and_chart(filled):
    assert card(run(ii, filled, "month_table"))["rows"][-1][0] == "Total"
    c = card(run(ii, filled, "monthly_chart", months=6))
    assert c["kind"] == "chart" and c["chart"]["values"][-1] == 780


def test_passive_share_and_stream_share(filled):
    out = run(ii, filled, "passive_share")
    c = card(out)
    assert c["kind"] == "incomestreams-bars" and len(c["data"]["rows"]) == 3
    assert card(run(ii, filled, "stream_share"))["data"]["rows"][0]["label"] == "Spare room"


def test_best_worst(filled):
    out = run(ii, filled, "best_worst")
    assert "Best: Spare room" in out and "Affiliate" in out
    assert card(out)["rows"][0][0] == "Best"


def test_growth(filled):
    rows = card(run(ii, filled, "growth"))["rows"]
    tik = next(r for r in rows if r[0] == "TikTok fund")
    assert tik[3].startswith("+")


def test_per_hour(filled):
    with pytest.raises(ValueError):
        run(ii, filled, "per_hour")
    run(ist, filled, "hours_log", stream="TikTok fund", hours=100, month="2026-09")
    run(ist, filled, "hours_log", stream="Affiliate", hours=5, month="2026-09")
    out = run(ii, filled, "per_hour")
    assert "Best pay per hour: Affiliate" in out and card(out)["kind"] == "table"


def test_diversification_and_reliance(filled, s):
    out = run(ii, filled, "diversification")
    assert "out of 100" in out and card(out)["kind"] == "incomestreams-bars"
    assert "No single" in run(ii, filled, "reliance_check", threshold=80)
    warned = run(ii, filled, "reliance_check", threshold=30)
    assert "Careful" in warned and "Spare room" in warned and card(warned)["kind"] == "list"


def test_reliance_single_stream(s):
    run(ist, s, "stream_add", name="Solo")
    run(ist, s, "income_log", stream="Solo", amount=100)
    out = run(ii, s, "diversification")
    assert "score 0" in out
    assert "Careful" in run(ii, s, "reliance_check")


def test_compare_run_rate_year_net_missing(filled):
    assert card(run(ii, filled, "compare_months", month_a="2026-08", month_b="2026-09"))["rows"][-1] == ["Total", "£660", "£780", "£120"]
    rr = run(ii, filled, "run_rate")
    assert "not a forecast" in rr and card(rr)["rows"][0][1] == "£566.67"
    assert card(run(ii, filled, "yearly_summary", year=2026))["rows"][-1][0] == "Total"
    assert card(run(ii, filled, "net_profit"))["rows"][-1][3]
    run(ist, filled, "stream_add", name="Newbie")
    gaps = run(ii, filled, "missing_months")
    assert "Newbie" in card(gaps)["items"][0]["label"]


# ---- Goals ------------------------------------------------------------------------------------------

def test_goal_set_show_pace_history_remove(filled):
    out = run(ig, filled, "goal_set", name="Extra 1000", target=1000, period="monthly")
    assert card(out)["kind"] == "incomestreams-bars" and "£780 of £1,000" in out
    run(ig, filled, "goal_set", name="Room", target=3000, period="tax_year", stream="Spare room")
    bars = card(run(ig, filled, "goal_show"))["data"]["rows"]
    assert len(bars) == 2 and bars[1]["value"] == 1800
    pace = run(ig, filled, "goal_pace", name="Extra 1000")
    assert "£220 to go" in pace and card(pace)["kind"] == "table"
    hist = run(ig, filled, "goal_history", name="Extra 1000", months=6)
    assert "0 of the last 6" in hist
    with pytest.raises(ValueError):
        run(ig, filled, "goal_history", name="Room")
    with pytest.raises(ValueError):
        run(ig, filled, "goal_set", target=5, period="weekly")
    assert "confirm" in run(ig, filled, "goal_remove", name="Room")
    run(ig, filled, "goal_remove", name="Room", confirmed=True)
    assert len(card(run(ig, filled, "goal_show"))["data"]["rows"]) == 1


def test_goal_none_and_reached(filled):
    with pytest.raises(ValueError):
        run(ig, filled, "goal_show")
    run(ig, filled, "goal_set", target=500, period="monthly")
    assert "reached" in run(ig, filled, "goal_pace")


def test_log_nudge(filled):
    run(ist, filled, "stream_add", name="Newbie")
    out = run(ig, filled, "log_nudge")
    assert "1 stream" in out and card(out)["items"][0]["say"]
    run(ist, filled, "income_log", stream="Newbie", amount=5)
    assert "Every active" in run(ig, filled, "log_nudge")


# ---- UK tax helpers ---------------------------------------------------------------------------------

def test_allowance_tracker(filled):
    out = run(it, filled, "allowance_tracker")
    assert "GOV.UK" in out and card(out)["data"]["rows"][0]["warn"] is True
    assert card(out)["data"]["rows"][1]["value"] == 1000
    with pytest.raises(ValueError):
        run(it, Settings(memory_dir=str(filled.memory_dir) + "-none"), "allowance_tracker")


def test_allowance_under(s):
    run(ist, s, "stream_add", name="Vinted")
    run(ist, s, "income_log", stream="Vinted", amount=300)
    assert "£700 to go" in run(it, s, "allowance_tracker")


def test_explained_and_or_expenses(filled):
    assert "1,000" in run(it, filled, "allowance_explained")
    out = run(it, filled, "allowance_or_expenses", gross=3000, costs=500)
    assert "£2,000" in out and card(out)["rows"][2][1] == "£2,000"
    assert "Under the allowance" in run(it, filled, "allowance_or_expenses", gross=800, costs=0)


def test_deadlines_and_register_help(s):
    out = run(it, s, "deadlines")
    c = card(out)
    assert c["items"][0]["label"].startswith("5 October 2026 (6 days)")
    assert any("31 January 2027" in i["label"] for i in c["items"][:-1])
    reg = run(it, s, "register_help")
    assert "6 days" in reg and "GOV.UK" in reg
    assert card(run(it, s, "tax_year_dates"))["rows"][1][1] == "6 April 2026"


def test_setaside(filled):
    out = run(it, filled, "setaside_show")
    assert "20%" in out and "rough" in out.lower() and card(out)["kind"] == "incomestreams-bars"
    out = run(it, filled, "setaside_set", percent=25)
    assert "25%" in out
    with pytest.raises(ValueError):
        run(it, filled, "setaside_set", percent=90)
    assert "£100" in run(it, filled, "setaside_add", amount=100, date="2026-09-01")
    assert card(run(it, filled, "setaside_show"))["data"]["rows"][0]["value"] == 100
    tax_2025 = run(it, filled, "setaside_show", tax_year_start=2025)
    assert "2025/26" in tax_2025


def test_taxyear_summary_and_csv(filled, tmp_path):
    out = run(it, filled, "taxyear_summary")
    rows = card(out)["rows"]
    assert rows[-2][0] == "Total" and "not tax advice" in card(out)["title"]
    exported = run(it, filled, "taxyear_csv")
    assert card(exported)["kind"] == "file"
    path = tmp_path / "Income streams" / "income 2026-27.csv"
    lines = list(csv.reader(open(path, encoding="utf-8")))
    assert lines[0][0] == "Date" and len(lines) == 19
    with pytest.raises(ValueError):
        run(it, filled, "taxyear_csv", tax_year_start=2020)


def test_records_checklist(s):
    c = card(run(it, s, "records_checklist"))
    assert len(c["items"]) == 10 and not c["items"][0]["done"]
    out = run(it, s, "records_tick", items=[1, 3])
    assert [i["done"] for i in card(out)["items"][:3]] == [True, False, True]
    out = run(it, s, "records_tick", items=[1], done=False)
    assert not card(out)["items"][0]["done"]
    with pytest.raises(ValueError):
        run(it, s, "records_tick", items=[99])


def test_receipts(filled):
    first = run(it, filled, "receipts_add", what="Ring light", amount=25, stream="TikTok", where="Drawer")
    rid = int(first.split("receipt ")[1].split(":")[0])
    run(it, filled, "receipts_add", what="Postage", amount=4.5, date="2025-01-01")
    with pytest.raises(ValueError):
        run(it, filled, "receipts_add", what="", amount=5)
    all_rows = card(run(it, filled, "receipts_list"))["rows"]
    assert len(all_rows) == 2
    assert len(card(run(it, filled, "receipts_list", stream="TikTok fund"))["rows"]) == 1
    assert len(card(run(it, filled, "receipts_list", tax_year_start=2026))["rows"]) == 1
    assert "confirm" in run(it, filled, "receipts_remove", id=rid)
    run(it, filled, "receipts_remove", id=rid, confirmed=True)
    assert len(card(run(it, filled, "receipts_list"))["rows"]) == 1


@pytest.mark.parametrize("action", ["what_counts", "allowable_costs", "payments_on_account", "gov_pointers"])
def test_guides_mention_govuk(s, action):
    out = run(it, s, action)
    assert "GOV.UK" in out and card(out)["kind"] == "list"


# ---- Wiring -----------------------------------------------------------------------------------------

def test_definitions_and_actions_match():
    for mod in (ist, ii, ig, it):
        tool = mod.tool_definitions()[0]
        assert tool["name"] in mod.NAMES and tool["input_schema"]["additionalProperties"] is False
        assert tool["input_schema"]["properties"]["action"]["enum"] == mod.ACTIONS
        assert len(mod.ACTIONS) == len(set(mod.ACTIONS))


def test_unknown_action(s):
    with pytest.raises(ValueError):
        run(ist, s, "nope")


def test_through_tools_run_tool(s):
    asyncio.run(tools._run_tool("income_streams", {"action": "stream_add", "name": "Etsy"}, s, None, None))
    said = asyncio.run(tools._run_tool("income_goals", {"action": "log_nudge"}, s, None, None))
    assert isinstance(said, screen.Shown) and said.card["kind"] == "list"
    with pytest.raises(ValueError):
        asyncio.run(tools._run_tool("income_tax_uk", {"action": "taxyear_csv"}, s, None, None))
