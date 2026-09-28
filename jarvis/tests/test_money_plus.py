import asyncio
import csv
from datetime import date, datetime

import httpx
import pytest

import finance_budget
import finance_friends
import finance_plan
import finance_pots
import homehouse
import homestore
import money
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: datetime(2026, 9, 28, 10, 30))  # a Monday
    return Settings(memory_dir=str(tmp_path), currency="GBP")


def spend(s, day, amount, what, category):
    money.log_spend(s, {"amount": amount, "what": what, "category": category}, date.fromisoformat(day))


def budgets(s, **args):
    return finance_budget.run_tool("money_budgets", args, s)


def pots(s, **args):
    return finance_pots.run_tool("money_pots", args, s)


def plan(s, http=None, **args):
    return asyncio.run(finance_plan.run_tool("money_planner", args, s, http))


def friends(s, **args):
    return finance_friends.run_tool("money_friends", args, s)


def sections(shown, kind):
    assert shown.card["kind"] == "finance"
    return [x for x in shown.card["data"]["sections"] if x["type"] == kind]


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"money_budgets", "money_pots", "money_planner", "money_friends"} <= names
    for module in (finance_budget, finance_pots, finance_plan, finance_friends):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
    assert "finance" in screen.EXTRA_KINDS


def test_budgets_left_and_warnings(s):
    assert budgets(s, action="budget_set", category="Food", amount=300) == "The food budget is 300.00 GBP a month."
    budgets(s, action="budget_set", category="fun", amount=50)
    budgets(s, action="budget_set", category="transport", amount=100)
    spend(s, "2026-09-02", 180, "Tesco", "food")
    spend(s, "2026-09-10", 60, "cinema", "fun")
    spend(s, "2026-09-11", 95, "train", "transport")
    shown = budgets(s, action="budget_left", category="food")
    assert shown == "You've 120.00 GBP left for food in September 2026."
    rows = sections(shown, "meters")[0]["rows"]
    assert [r["label"] for r in rows] == ["food", "fun", "transport"] and rows[1]["over"] is True
    assert "used 335.00 GBP of 450.00 GBP" in budgets(s, action="budget_left")
    warn = budgets(s, action="over_budget")
    assert warn.startswith("1 over budget, 1 close to the limit: fun: 10.00 GBP over")
    assert warn.card["kind"] == "list" and len(warn.card["items"]) == 2
    assert budgets(s, action="budget_set", category="fun", amount=0).startswith("Ask the user to confirm")
    assert budgets(s, action="budget_set", category="fun", amount=0, confirmed=True) == "Removed the fun budget."


def test_trends_and_recurring(s):
    for month, food in (("2026-04", 200), ("2026-05", 210), ("2026-06", 190), ("2026-07", 200), ("2026-08", 320)):
        spend(s, f"{month}-05", food, "shopping", "food")
        spend(s, f"{month}-14", 10.99, "Netflix", "fun")
    spend(s, "2026-09-14", 10.99, "netflix", "fun")
    spend(s, "2026-08-20", 45, "shoes", "clothes")
    shown = budgets(s, action="trends")
    assert "food: up 120.00 GBP in August 2026" in shown
    chart = sections(shown, "chart")[0]["chart"]
    assert chart["labels"] == ["Apr", "May", "Jun", "Jul", "Aug", "Sep"] and chart["values"][-1] == 10.99
    one = budgets(s, action="trends", category="food")
    assert sections(one, "chart")[0]["chart"]["values"] == [200, 210, 190, 200, 320, 0]
    rec = budgets(s, action="recurring")
    assert rec.startswith("Likely subscriptions: netflix about 10.99 GBP (6 months)")
    assert "shopping" not in rec and rec.card["items"][0]["say"] == "Add netflix to my subscriptions at 10.99 a month."


def test_report_tax_year_and_export(s):
    money.log_payslip(s, {"month": "2026-09", "employer": "VGC", "net": 2300, "gross": 3000, "tax": 400}, date(2026, 9, 28))
    money.log_payslip(s, {"month": "2026-03", "employer": "VGC", "net": 2000}, date(2026, 9, 28))
    spend(s, "2026-09-03", 50, "lunch, with Sam", "food")
    budgets(s, action="budget_set", category="food", amount=200)
    pots(s, action="pot_create", name="Holiday", target=1000)
    pots(s, action="pot_add", name="holiday", amount=150)
    rep = budgets(s, action="report")
    assert rep == "In September 2026 you took home 2,300.00 GBP, spent 50.00 GBP and put 150.00 GBP into savings pots."
    assert sections(rep, "stats")[0]["items"][2] == {"label": "Left over", "value": "2,250.00 GBP"}
    assert sections(rep, "meters") and sections(rep, "table")[0]["rows"] == [["Holiday", "+150.00"]]
    tax = budgets(s, action="tax_year")
    assert tax.startswith("Tax year 2026/27: take-home 2,300.00 GBP, spending 50.00 GBP, saved into pots 150.00 GBP.")
    assert len(sections(tax, "chart")[0]["chart"]["values"]) == 12
    assert "take-home 2,000.00 GBP" in budgets(s, action="tax_year", year=2025)
    out = budgets(s, action="export")
    assert out.card["kind"] == "file" and out.card["mime"] == "text/csv"
    path = s.memory_dir + "/Personal/money export 2026-09-28.csv"
    with open(path, encoding="utf-8") as f:
        lines = list(csv.reader(f))
    assert lines[0][-1] == "amount GBP" and all(len(r) == 5 for r in lines)
    assert ["spending", "2026-09-03", "lunch with Sam", "food", "50.00"] in lines


def test_pots(s):
    assert pots(s, action="pots").startswith("No savings pots yet")
    assert pots(s, action="pot_create", name="Car", target=2000).startswith("The Car pot has a target of 2,000.00 GBP")
    shown = pots(s, action="pot_add", name="car", amount=500)
    assert shown == "Added 500.00 GBP to Car. It has 500.00 GBP, 25% of the target."
    assert sections(shown, "meters")[0]["rows"][0]["value"] == 500
    assert pots(s, action="pot_withdraw", name="car", amount=100).startswith("Took 100.00 GBP from Car")
    with pytest.raises(ValueError):
        pots(s, action="pot_withdraw", name="car", amount=1000)
    assert pots(s, action="pots").card["id"] == "finance-pots"
    assert pots(s, action="pot_remove", name="car").startswith("Ask the user")
    assert pots(s, action="pot_remove", name="car", confirmed=True) == "Deleted the Car pot."


def test_envelopes(s):
    assert pots(s, action="envelope_set", name="Groceries", amount=200) == "The Groceries envelope has 200.00 GBP."
    shown = pots(s, action="envelope_spend", name="groceries", amount=35.5, what="market")
    assert shown == "Spent 35.50 GBP from Groceries; 164.50 GBP left."
    assert sections(shown, "meters")[0]["rows"][0]["note"] == "164.50 GBP left of 200.00 GBP"
    with pytest.raises(ValueError):
        pots(s, action="envelope_spend", name="groceries", amount=500)
    assert pots(s, action="envelopes").startswith("Envelopes: Groceries 164.50 GBP left")


def test_net_worth(s):
    pots(s, action="networth_add", date="2026-08-01", assets=[{"name": "Savings", "amount": 5000}],
         liabilities=[{"name": "Card", "amount": 1000}])
    shown = pots(s, action="networth_add", assets=[{"name": "Savings", "amount": 6000}, {"name": "Pension", "amount": 2000}],
                 liabilities=[{"name": "Card", "amount": 500}])
    assert shown == "Net worth on Monday 28 September: 7,500.00 GBP. That's up 3,500.00 GBP since 2026-08-01."
    assert sections(shown, "chart")[0]["chart"]["values"] == [4000, 7500]
    assert pots(s, action="networth").card["id"] == "finance-networth"
    with pytest.raises(ValueError):
        pots(s, action="networth_add")


def test_receipts(s, tmp_path):
    (tmp_path / "Shopping").mkdir(parents=True)
    (tmp_path / "Shopping" / "kettle receipt.jpg").write_bytes(b"\xff\xd8")
    assert pots(s, action="receipt_add", shop="Argos", amount=39.99, item="kettle", warranty_months=24,
                photo="kettle receipt.jpg", folder="Shopping", date="2026-09-01") == \
        "Saved the Argos receipt for kettle: 39.99 GBP on 2026-09-01."
    pots(s, action="receipt_add", shop="Currys", amount=499, item="TV")
    photo = pots(s, action="receipt_find", query="kettle")
    assert photo.card["kind"] == "file" and "warranty until 2028-09-01" in photo
    table = pots(s, action="receipt_find", query="")
    assert table.startswith("2 receipts found") and len(sections(table, "table")[0]["rows"]) == 2
    assert pots(s, action="receipt_find", query="sofa") == "No receipts match sofa."


def test_debt_plan(s):
    assert plan(s, action="debt_plan").startswith("No debts")
    plan(s, action="debt_set", name="Card", balance=2000, apr=24, minimum=60)
    plan(s, action="debt_set", name="Loan", balance=500, apr=6, minimum=10)
    shown = plan(s, action="debt_plan", extra=100)
    assert shown.startswith("Avalanche clears everything by") and "saves" in shown
    stats = {i["label"]: i["value"] for i in sections(shown, "stats")[0]["items"]}
    assert stats["Snowball done"] and stats["Avalanche interest"].endswith("GBP")
    charts = sections(shown, "chart")
    assert len(charts) == 2 and charts[0]["chart"]["values"][0] == 2500
    order = sections(shown, "table")[0]["rows"]
    assert order[0][1].startswith("Loan") and order[0][2].startswith("Card")
    plan(s, action="debt_set", name="Card", balance=2000, apr=24, minimum=10)
    with pytest.raises(ValueError):
        finance_plan.simulate(finance_plan.fs.rows(s, finance_plan.fs.DEBTS), -50, "snowball")
    assert plan(s, action="debt_remove", name="loan", confirmed=True) == "Removed the Loan debt."


def test_payday_rules(s):
    assert plan(s, action="payday").startswith("I don't know when payday is")
    assert plan(s, action="payday_set", rule="last_working_day") == "Got it. Next payday is Wednesday 30 September."
    assert plan(s, action="payday_set", rule="day_of_month", day=4) == "Got it. Next payday is Friday 2 October."
    assert plan(s, action="payday_set", rule="every_weeks", weeks=4, start="2026-09-10") == \
        "Got it. Next payday is Thursday 8 October."
    shown = plan(s, action="payday", balance=400)
    assert shown == "10 days until payday on Thursday 8 October. With 400.00 GBP that's 40.00 GBP a day."
    assert shown.card["kind"] == "timer" and shown.card["ends_at"] > 0


def test_afford(s):
    plan(s, action="payday_set", rule="day_of_month", day=15)
    homehouse.bill_add(s, "Rent", 900, 1)
    homehouse.bill_add(s, "Phone", 20, 20)
    budgets(s, action="budget_set", category="food", amount=300)
    spend(s, "2026-09-05", 250, "food shop", "food")
    yes = plan(s, action="afford", price=100, balance=1200)
    assert yes == "Yes. After bills and budgets until Thursday 15 October you'd have 150.00 GBP spare."
    assert sections(yes, "table")[0]["rows"] == [["2026-10-01", "Rent", "900.00"]]
    no = plan(s, action="afford", price=500, balance=1200)
    assert no.startswith("Not really: you'd be 250.00 GBP short")


def test_per_use_and_habit(s):
    assert plan(s, action="per_use", price=120, uses=300) == "120.00 GBP over 300 uses is 0.40 GBP a use."
    shown = plan(s, action="habit_cost", price=3.5, per_week=5, what="Coffee")
    assert shown == "Coffee costs 910.00 GBP a year, about 75.83 GBP a month."
    assert sections(shown, "stats")[0]["items"][3]["value"] == "4,550.00 GBP"


def test_trip_budget(s):
    def handler(request):
        assert request.url.params["from"] == "EUR" and request.url.params["to"] == "GBP"
        return httpx.Response(200, json={"date": "2026-09-25", "rates": {"GBP": 86.0}})

    assert plan(s, action="trip_set", name="Spain", currency="eur", budget=800) == \
        "The Spain trip has a budget of 800.00 EUR."
    plan(s, action="trip_spend", name="spain", amount=60, what="tapas")
    assert plan(s, action="trip_spend", name="spain", amount=40, what="museum") == \
        "Logged 40.00 EUR on the Spain trip; 700.00 EUR of the budget left."

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await finance_plan.run_tool("money_planner", {"action": "trip_total", "name": "spain"}, s, http)

    shown = asyncio.run(go())
    assert shown.startswith("The Spain trip: 100.00 EUR spent of 800.00 EUR. 100.00 EUR is 86.00 GBP")
    assert len(sections(shown, "table")[0]["rows"]) == 2

    async def offline():
        def fail(request):
            raise httpx.ConnectError("no internet")
        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as http:
            return await finance_plan.trip_total(s, http, "spain")

    assert "couldn't get an exchange rate" in asyncio.run(offline())
    with pytest.raises(ValueError):
        plan(s, action="trip_set", name="x", currency="euros", budget=1)


def test_ious_split_settle_simplify(s):
    assert friends(s, action="balances") == "Nobody owes anybody anything."
    assert friends(s, action="split", payer="me", amount=90, people=["sam", "alex"], what="dinner") == \
        "Split 90.00 GBP 3 ways: 30.00 GBP each, owed to me."
    assert friends(s, action="owe", person="alex", to="sam", amount=20, what="taxi") == \
        "Noted: Alex owes Sam 20.00 GBP for taxi."
    friends(s, action="owe", person="me", to="alex", amount=5)
    shown = friends(s, action="balances")
    assert shown == "Overall you're owed 55.00 GBP."
    rows = sections(shown, "table")[0]["rows"]
    assert rows[0] == ["Me", "+55.00", "is owed"]
    simple = friends(s, action="simplify")
    assert simple == "2 payments would clear everything: Alex owes me 45.00 GBP; Sam owes me 10.00 GBP."
    assert simple.card["kind"] == "list"
    assert friends(s, action="settle", person="sam") == "Recorded Sam paying me 30.00 GBP. All square now."
    assert friends(s, action="settle", person="sam") == "Sam doesn't owe me anything."
    assert friends(s, action="settle", person="alex", amount=10) == \
        "Recorded Alex paying me 10.00 GBP. Alex still owes 15.00 GBP."
    with pytest.raises(ValueError):
        friends(s, action="split", payer="me", amount=10, people=[])
