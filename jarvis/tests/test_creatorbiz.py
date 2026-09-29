import asyncio
from pathlib import Path

import pytest

import creatorbiz_deals
import creatorbiz_docs
import creatorbiz_money
import creatorbiz_store as cb
import creatorbiz_work
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def deals(s, **a):
    return creatorbiz_deals.run_tool("creator_deals", a, s)


def work(s, **a):
    return creatorbiz_work.run_tool("creator_work", a, s)


def money(s, **a):
    return creatorbiz_money.run_tool("creator_money", a, s)


def docs(s, **a):
    return creatorbiz_docs.run_tool("creator_docs", a, s)


def test_registered_and_through_tools(s):
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"creator_deals", "creator_work", "creator_money", "creator_docs"} <= names
    assert {"creatorbiz-pipeline", "creatorbiz-ratecard", "creatorbiz-invoices", "creatorbiz-checklist"} <= screen.EXTRA_KINDS
    out = asyncio.run(tools._run_tool("creator_deals", {"action": "add", "brand": "Glow", "fee": 500}, s, None))
    assert isinstance(out, screen.Shown) and out.card["kind"] == "creatorbiz-pipeline"


def test_deal_pipeline(s):
    shown = deals(s, action="add", brand="Glow", campaign="Summer", fee=500, stage="pitched")
    assert shown.card["data"]["cards"][0]["stage"] == "pitched"
    assert shown.card["data"]["cards"][0]["follow_up"] == "in 7 days"
    with pytest.raises(ValueError):
        deals(s, action="add", brand="glow", campaign="summer")
    assert deals(s, action="move", brand="glow", stage="negotiating").card["data"]["cards"][0]["stage"] == "negotiating"
    with pytest.raises(ValueError):
        deals(s, action="move", brand="glow", stage="bogus")
    assert deals(s, action="pipeline").card["kind"] == "creatorbiz-pipeline"
    assert deals(s, action="list").card["rows"][0][:3] == ["Glow - Summer", "negotiating", "£500"]
    assert deals(s, action="list", stage="paid").startswith("No brand deals")
    updated = deals(s, action="update_terms", brand="Glow", usage_rights="3 months paid ads", payment_days=30, fee=600)
    assert updated.card["kind"] == "creatorbiz-pipeline"
    detail = deals(s, action="show", brand="Glow")
    assert "3 months paid ads" in detail.card["text"] and "£600" in detail.card["text"]
    assert deals(s, action="notes", brand="Glow").startswith("No notes")
    deals(s, action="note", brand="Glow", text="Asked for a call")
    assert deals(s, action="notes", brand="Glow").card["items"][0]["label"] == "Asked for a call"
    with pytest.raises(ValueError):
        deals(s, action="show", brand="Nobody")


def test_follow_ups_and_value(s):
    deals(s, action="add", brand="Glow", stage="pitched", follow_up="yesterday")
    due = deals(s, action="follow_ups")
    assert due.card["kind"] == "list" and "Glow" in due.card["items"][0]["say"]
    assert "again in a week" in deals(s, action="followed_up", brand="Glow")
    assert deals(s, action="follow_ups").startswith("No brand follow-ups")
    assert "Cleared" in deals(s, action="set_follow_up", brand="Glow")
    assert "nudge you" in deals(s, action="set_follow_up", brand="Glow", follow_up="tomorrow")
    assert deals(s, action="pipeline_value").startswith("None of your deals")
    deals(s, action="add", brand="Acme", fee=800, stage="agreed")
    value = deals(s, action="pipeline_value")
    assert "£800" in value and "not guaranteed" in value and value.card["kind"] == "table"


def test_remove_needs_confirmation(s):
    deals(s, action="add", brand="Glow")
    assert "really remove" in deals(s, action="remove", brand="Glow")
    assert len(cb.deals(s)) == 1
    assert deals(s, action="remove", brand="Glow", confirmed=True).startswith("Removed")
    assert cb.deals(s) == []


def test_deliverables(s):
    deals(s, action="add", brand="Glow", stage="agreed")
    assert work(s, action="deliverables").startswith("No deliverables")
    assert "due" in work(s, action="add_deliverable", brand="Glow", title="1 reel", platform="Instagram", due="tomorrow")
    work(s, action="add_deliverable", brand="Glow", title="Story set", due="2099-01-01")
    with pytest.raises(ValueError):
        work(s, action="add_deliverable", brand="Glow", title="1 REEL")
    table = work(s, action="deliverables")
    assert table.card["kind"] == "table" and table.card["rows"][0][1] == "1 reel" and table.card["rows"][0][4] == "tomorrow"
    soon = work(s, action="due_soon")
    assert soon.card["kind"] == "list" and len(soon.card["items"]) == 1
    assert "1 left" in work(s, action="done", brand="Glow", title="reel")
    assert "consider invoicing" in work(s, action="done", brand="Glow", title="story")
    assert work(s, action="due_soon").startswith("No brand deliverables")
    assert work(s, action="reopen", brand="Glow", title="reel").startswith("Reopened")
    assert work(s, action="deliverables", brand="Glow").card["rows"][0][4] in ("tomorrow", "done")
    assert work(s, action="remove_deliverable", brand="Glow", title="story").startswith("Removed")
    with pytest.raises(ValueError):
        work(s, action="done", brand="Glow", title="nothing")


def test_gifts_and_affiliates(s):
    assert work(s, action="gifts").startswith("No gifted")
    added = work(s, action="add_gift", brand="Lush", item="Face mask", value=12.5)
    assert added.card["kind"] == "table" and "ASA" in added
    updated = work(s, action="gift_status", brand="lush", status="posted", labelled=True)
    assert updated.card["rows"][0][3:] == ["posted", "yes"]
    with pytest.raises(ValueError):
        work(s, action="gift_status", brand="lush", status="sold")
    assert work(s, action="gifts", brand="Lush").card["rows"][0][2] == "£12.50"
    assert "£12.50" in work(s, action="gifts_value") and "GOV.UK" in work(s, action="gifts_value")
    assert work(s, action="affiliates").startswith("No affiliate")
    assert work(s, action="add_affiliate", brand="Amazon", code="ME10", commission="4%").card["rows"][0][0] == "Amazon"
    with pytest.raises(ValueError):
        work(s, action="add_affiliate", brand="amazon")
    earned = work(s, action="affiliate_earning", brand="amazon", amount=7.5)
    assert earned.card["rows"][0][3] == "£7.50"
    assert cb.ledger(s)[0]["category"] == "affiliate"
    assert work(s, action="affiliates").card["rows"][0][3] == "£7.50"
    with pytest.raises(ValueError):
        work(s, action="affiliate_earning", brand="Nobody", amount=1)


def test_rate_card_is_an_estimate(s):
    with pytest.raises(ValueError):
        money(s, action="rate_card")
    card = money(s, action="rate_card", avg_views=10000, cpm_low=10, cpm_high=20)
    assert card.card["kind"] == "creatorbiz-ratecard" and "not a promise" in card
    assert card.card["data"]["rows"][0] == {"format": "main video or reel", "low": 100, "high": 200}
    saved = money(s, action="save_rates", avg_views=10000, hourly_rate=50, hours=4)
    assert saved.card["data"]["rows"][0]["low"] == 200  # time-based floor
    assert money(s, action="rate_card").card["data"]["views"] == 10000
    with pytest.raises(ValueError):
        money(s, action="save_rates", hourly_rate=-1)


def test_package_quote(s):
    money(s, action="save_rates", avg_views=10000, cpm_low=10, cpm_high=20)
    quote = money(s, action="package_quote", counts={"main video or reel": 2, "story set": 1}, usage_rights=True, discount_pct=10)
    assert quote.card["kind"] == "table" and quote.card["rows"][-1][0].startswith("Total (after 10% off)")
    with pytest.raises(ValueError):
        money(s, action="package_quote")
    with pytest.raises(ValueError):
        money(s, action="package_quote", counts={"story set": 1}, discount_pct=100)


def test_invoice_lifecycle(s):
    deals(s, action="add", brand="Glow", stage="delivered", payment_days=14, fee=500)
    with pytest.raises(ValueError):
        money(s, action="invoice_create", brand="Glow")
    made = money(s, action="invoice_create", brand="Glow", amount=500, description="One reel", campaign="Summer", vat_percent=20)
    assert made.card["kind"] == "creatorbiz-invoices"
    inv = made.card["data"]["invoices"][0]
    assert inv["number"].endswith("-001") and inv["total"] == "£600" and inv["status"] == "unpaid"
    assert cb.deals(s)[0]["stage"] == "invoiced"
    assert cb.load(s, cb.INVOICES, [])[0]["payment_days"] == 14
    files = list((Path(s.memory_dir) / cb.FOLDER).glob("Invoice*.md"))
    assert files and "VAT 20%" in files[0].read_text(encoding="utf-8")
    shown = money(s, action="invoice_show", brand="Glow")
    assert shown.card["kind"] == "text" and "£600" in shown.card["text"]
    assert money(s, action="overdue") == "No invoices are overdue."
    old = money(s, action="invoice_create", brand="Zed", items=[{"description": "Post", "amount": 100}], issued="2020-01-01",
                payment_days=30)
    assert old.card["data"]["invoices"][1]["status"] == "overdue"
    assert money(s, action="overdue").card["data"]["invoices"][0]["brand"] == "Zed"
    assert money(s, action="invoices", status="overdue").card["data"]["invoices"][0]["brand"] == "Zed"
    with pytest.raises(ValueError):
        money(s, action="invoices", status="late")
    chase = money(s, action="chase_draft", brand="Zed", level=3)
    assert "GOV.UK" in chase.card["text"] and "have not sent" in chase
    paid = money(s, action="mark_paid", brand="Glow")
    assert paid.card["data"]["invoices"][0]["status"] == "paid"
    assert cb.deals(s)[0]["stage"] == "paid"
    assert cb.ledger(s)[0]["amount"] == 600
    with pytest.raises(ValueError):
        money(s, action="mark_paid", number=cb.load(s, cb.INVOICES, [])[0]["number"])
    with pytest.raises(ValueError):
        money(s, action="chase_draft", number=cb.load(s, cb.INVOICES, [])[0]["number"])
    number = cb.load(s, cb.INVOICES, [])[1]["number"]
    assert "really remove" in money(s, action="remove_invoice", number=number)
    assert money(s, action="remove_invoice", number=number, confirmed=True).startswith("Removed")
    assert len(cb.load(s, cb.INVOICES, [])) == 1


def test_invoice_due_date(s):
    assert "Friday 31 January 2025" in money(s, action="invoice_due_date", issued="2025-01-01", payment_days=30)
    with pytest.raises(ValueError):
        money(s, action="invoice_due_date", payment_days=999)


def test_ledger_and_summaries(s):
    assert money(s, action="expenses").startswith("No creator expenses")
    assert "£40" in money(s, action="add_expense", amount=40, category="Equipment", brand="Glow")
    money(s, action="add_expense", amount=10, category="software")
    assert "income" in money(s, action="add_income", amount="£250", brand="Glow", note="Deposit")
    with pytest.raises(ValueError):
        money(s, action="add_income", amount="lots")
    with pytest.raises(ValueError):
        money(s, action="add_expense", amount=-5)
    exp = money(s, action="expenses")
    assert exp.card["kind"] == "chart" and exp.card["chart"]["labels"][0] == "equipment"
    assert money(s, action="expenses", category="software").card["chart"]["values"] == [10.0]
    deals(s, action="add", brand="Glow", fee=500)
    summary = money(s, action="deal_summary", brand="Glow")
    assert ["Received", "£250"] in summary.card["rows"] and ["Left after expenses", "£210"] in summary.card["rows"]
    month = money(s, action="month_summary")
    assert month.card["kind"] == "chart" and len(month.card["chart"]["labels"]) == 6 and month.card["chart"]["values"][-1] == 200
    with pytest.raises(ValueError):
        money(s, action="month_summary", month="soon")
    tax = money(s, action="tax_year_summary")
    assert "GOV.UK" in tax and tax.card["kind"] == "table"
    old = money(s, action="tax_year_summary", tax_year_start=2001)
    assert ["Income", "£0"] in old.card["rows"]


def test_media_kit(s, tmp_path):
    with pytest.raises(ValueError):
        docs(s, action="kit_show")
    with pytest.raises(ValueError):
        docs(s, action="kit_set")
    assert "niche" in docs(s, action="kit_set", name="Sam", niche="Baking", bio="I bake <b>cakes</b>", avg_views=12000,
                           platforms="TikTok 12k", contact="sam@example.com")
    assert docs(s, action="kit_show").card["kind"] == "text"
    md = docs(s, action="kit_build")
    assert md.card["kind"] in ("file", "text") and "Media kit.md" in md
    page = docs(s, action="kit_build", format="html")
    html_text = (tmp_path / cb.FOLDER / "Media kit.html").read_text(encoding="utf-8")
    assert "&lt;b&gt;cakes" in html_text and "<b>cakes</b>" not in html_text and page.card
    assert "12,000" in (tmp_path / cb.FOLDER / "Media kit.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        docs(s, action="kit_build", format="pdf")
    assert money(s, action="rate_card").card["data"]["views"] == 12000


def test_drafts_never_sent(s, tmp_path):
    docs(s, action="kit_set", name="Sam", niche="Baking")
    for action, args in [("pitch_draft", {"idea": "A bake-along"}), ("followup_draft", {}), ("negotiation_draft", {"fee": 750}),
                         ("decline_draft", {"reason": "the timing is wrong"})]:
        out = docs(s, action=action, brand="Glow", **args)
        assert out.card["kind"] == "text" and "not sent anything" in out and "Sam" in out.card["text"]
    assert "£750" in (tmp_path / cb.FOLDER / "Reply to Glow offer (draft).md").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        docs(s, action="pitch_draft")


def test_contract_checklist(s):
    general = docs(s, action="contract_checklist")
    assert general.card["kind"] == "creatorbiz-checklist" and "not legal advice" in general
    assert len(general.card["data"]["items"]) == 12
    deals(s, action="add", brand="Glow")
    ticked = docs(s, action="contract_tick", brand="Glow", item="payment")
    assert sum(i["ticked"] for i in ticked.card["data"]["items"]) == 1
    docs(s, action="contract_tick", brand="Glow", item="Usage rights")
    assert docs(s, action="contract_checklist", brand="Glow").startswith("2 of 12")
    unticked = docs(s, action="contract_tick", brand="Glow", item="payment", ticked=False)
    assert sum(i["ticked"] for i in unticked.card["data"]["items"]) == 1
    with pytest.raises(ValueError):
        docs(s, action="contract_tick", brand="Glow", item="banana")


def test_guides(s):
    for action in ["disclosure_guide", "usage_rights", "exclusivity", "payment_terms", "brand_questions", "red_flags", "tax_guide",
                   "negotiation_tips"]:
        out = docs(s, action=action)
        assert out.card["kind"] == "list" and out.card["items"]
    assert "ASA" in docs(s, action="disclosure_guide").card["items"][-1]["label"]
    assert "GOV.UK" in docs(s, action="tax_guide").card["items"][-1]["label"]
    assert "guaranteed" in docs(s, action="negotiation_tips").card["items"][-1]["label"]


def test_all_tools_have_schemas():
    for mod in (creatorbiz_deals, creatorbiz_work, creatorbiz_money, creatorbiz_docs):
        for t in mod.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False
            assert set(mod.ACTIONS) == set(t["input_schema"]["properties"]["action"]["enum"])
            assert t["name"] in mod.NAMES
