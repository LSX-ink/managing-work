import asyncio
import json
import subprocess
from datetime import date, datetime, timedelta

import pytest

import kinetic_briefing as kb
import kinetic_site as ksite
import kinetic_store as st
import memory
from config import Settings

NOW = datetime(2026, 10, 21, 10, 0)  # a fixed morning: nothing depends on the real clock
TODAY = NOW.date()
calls = []
BRIEF = {"id": 9, "created_at": int(NOW.timestamp() * 1000), "name": "Ada Lovelace", "business": "Ada's Salon",
         "email": "ada@salon.test", "phone": "", "data": json.dumps({"package": "Business website", "estimate": "£895"})}
ANSWERS = {
    "FROM signups WHERE marketing": [{"step": 1, "stopped": None, "n": 3}],
    "FROM signups WHERE created_at": [{"n": 4, "opted_in": 2}],
    "FROM briefs WHERE created_at": [BRIEF],
    "FROM payments": [
        {"kind": "payment", "status": "succeeded", "amount": 44750, "currency": "gbp", "customer": "Ada Lovelace",
         "description": "Deposit", "created": 1},
        {"kind": "payment", "status": "failed", "amount": 1000, "currency": "gbp", "customer": "Bob", "created": 1}],
}


def fake_run(answers, code=0):
    def run(cmd, **kw):
        calls.append(cmd[-1])
        rows = next((rows for key, rows in answers.items() if key in cmd[-1]), [])
        out = rows if isinstance(rows, str) else json.dumps([{"results": rows, "success": True}])
        return subprocess.CompletedProcess(cmd, code, stdout=out, stderr="")
    return run


@pytest.fixture(autouse=True)
def wrangler(monkeypatch):
    calls.clear()
    monkeypatch.setattr(ksite.subprocess, "run", fake_run(ANSWERS))
    monkeypatch.setattr(ksite.shutil, "which", lambda name: "npx")
    monkeypatch.setattr(st, "today", lambda: TODAY)


@pytest.fixture
def s(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    ago = lambda n: (TODAY - timedelta(days=n)).isoformat()  # noqa: E731
    st.save(s, st.OUTREACH, [
        {"id": 1, "name": "Joe's Barbers", "status": "contacted", "messages": 1, "last_contacted": ago(6),
         "channel": "email"},
        {"id": 2, "name": "Fresh Lead", "status": "new", "messages": 0}])
    st.save(s, st.PROSPECTS, [
        {"id": 1, "name": "Sam's Café", "website": "", "phone": "0161 000 0000"},
        {"id": 2, "name": "Good Site Ltd", "website": "https://good.test", "audit": {"grade": "good", "score": 90,
                                                                                    "problems": []}},
        {"id": 3, "name": "Broken Bakery", "website": "https://broken.test", "audit": {"grade": "down", "score": 0,
                                                                                      "problems": []}}])
    st.save(s, st.INVOICES, [
        {"id": 1, "number": "INV-0001", "client": "Ada's Salon", "total": 300, "due": ago(3), "status": "unpaid"},
        {"id": 2, "number": "INV-0002", "client": "Kim", "total": 150, "due": (TODAY + timedelta(days=5)).isoformat(),
         "status": "unpaid"},
        {"id": 3, "number": "INV-0003", "client": "Lee", "total": 500, "due": ago(9), "status": "paid"}])
    return s


def test_full_briefing(s):
    b = kb.gather(s, NOW)
    since = kb.start_of_yesterday(NOW)
    assert since == int(datetime(2026, 10, 20).astimezone().timestamp() * 1000)
    assert all("SELECT" in c and "'" not in c for c in calls) and f"created_at >= {since}" in calls[0]
    assert f"created >= {since}" in calls[2]
    text = kb.short_text(s, b)
    assert text == ("Since yesterday: 4 new sign-ups, 1 new brief (Ada's Salon), £447.50 paid by card. Today: 1 "
                    "follow-up due, 1 invoice overdue (£300). Contact today: Sam's Café, Broken Bakery, Good Site Ltd. "
                    "This week so far: 0 messages sent, 0 replies, 0 briefs, 0 payments. The step to fix is messages.")
    full = kb.full_text(s, b)
    for bit in ("# Morning briefing: 21 October 2026", "Sign-ups: 4 new, 2 ticked", "Ada Lovelace at Ada's Salon",
                "Paid: £447.50 from Ada Lovelace (Deposit)", "Failed: £10.00 from Bob", "Joe's Barbers: messaged 15 Oct",
                "INV-0001 Ada's Salon: £300, overdue 3 days", "INV-0002 Kim: £150, unpaid", "had email 1",
                "Sam's Café: No website, 0161 000 0000", "Broken Bakery: Website doesn't load"):
        assert bit in full, bit
    assert "INV-0003" not in full and "Fresh Lead" in kb.full_text(s, {**b, "contact": kb.contact_today(s, 5)})


def test_tool_saves_the_full_version_and_shows_it(s):
    out = asyncio.run(kb.run_tool("kinetic_briefing", {"action": "briefing"}, s))
    path = memory.root(s) / st.FOLDER / "Briefings" / f"Morning briefing {TODAY.isoformat()}.md"
    assert path.exists() and "## Who to contact today" in path.read_text(encoding="utf-8")
    assert out.startswith("Sir, your morning briefing. Since yesterday:") and out.card["kind"] == "file"
    assert st.load(s, kb.LAST_RUN, {}) == {"date": TODAY.isoformat()}
    assert "on the screen" in asyncio.run(kb.run_tool("kinetic_briefing", {"action": "last"}, s))


def test_without_wrangler_the_rest_still_comes(s, monkeypatch):
    def missing(cmd, **kw):
        calls.append(cmd[-1])
        raise FileNotFoundError
    monkeypatch.setattr(ksite.subprocess, "run", missing)
    b = kb.gather(s, NOW)
    assert len(calls) == 1  # no waiting on wrangler four times
    text = kb.short_text(s, b)
    assert text.startswith("Since yesterday: I couldn't reach the website's database.") and "1 follow-up due" in text
    full = kb.full_text(s, b)
    assert "Sign-ups: couldn't check (I need Node.js" in full and "Couldn't check payments" in full
    assert "INV-0001" in full


def test_no_payments_table_yet(s, monkeypatch):
    monkeypatch.setattr(ksite.subprocess, "run", _failing_payments(ANSWERS))
    b = kb.gather(s, NOW)
    assert "payments table isn't on the site's database yet" in kb.full_text(s, b)
    assert "4 new sign-ups" in kb.short_text(s, b) and "paid by card" not in kb.short_text(s, b)


def _failing_payments(answers):
    ok = fake_run(answers)

    def run(cmd, **kw):
        if "FROM payments" in cmd[-1]:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="no such table: payments")
        return ok(cmd, **kw)
    return run


def test_once_a_day_from_nine(s):
    assert kb.daily(s, datetime(2026, 10, 21, 8, 59)) == ("", "")
    spoken, shown = kb.daily(s, NOW)
    assert spoken.startswith("Good morning, sir. Your Kinetic briefing: Since yesterday: 4 new sign-ups")
    assert shown.startswith("Morning briefing. Since yesterday") and "Briefings/Morning briefing 2026-10-21.md" in shown
    assert kb.daily(s, NOW + timedelta(hours=3)) == ("", "")  # once a day, saved, so a restart doesn't repeat it
    assert kb.daily(s, NOW + timedelta(days=1))[0]


def test_watch_waits_for_a_page_and_never_hangs(s, monkeypatch):
    monkeypatch.setattr(kb, "FIRST_LOOK", 0)
    monkeypatch.setattr(kb, "daily", lambda settings: ("Good morning.", "Morning briefing. All quiet."))
    heard = []

    async def announce(text, kind, shown=None):
        heard.append((text, kind, shown))
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(asyncio.wait_for(kb.watch(s, announce, lambda: True), 10))
    assert heard == [("Good morning.", "briefing", "Morning briefing. All quiet.")]


def test_money():
    assert kb.money(44750, "gbp") == "£447.50" and kb.money(1000, "USD") == "$10.00"
    assert kb.money(500, "nok") == "5.00 NOK"
    assert date.fromisoformat("2026-10-21") == TODAY


def test_weekly_report_compares_the_week_just_gone_with_the_one_before(s):
    w = kb.weekly_gather(s, date(2026, 10, 26))  # a Monday
    assert (w["week"], w["sunday"]) == (date(2026, 10, 19), date(2026, 10, 25))
    assert (w["numbers"]["this"]["messages"], w["numbers"]["last"]["messages"]) == (0, 1)  # Joe's: the 15th
    assert kb.weekly_short(s, w).startswith("Week of 19 October: 0 messages sent (down from 1); 0 replies; ")
    assert "| Messages sent |" in kb.weekly_text(s, w)
    out = asyncio.run(kb.run_tool("kinetic_briefing", {"action": "weekly"}, s))
    assert "your weekly report" in out


def test_weekly_report_comes_once_on_monday_morning(s):
    assert kb.weekly_auto(s, datetime(2026, 10, 26, 8, 0)) == ("", "")  # before nine
    assert kb.weekly_auto(s, datetime(2026, 10, 27, 10, 0)) == ("", "")  # a Tuesday
    spoken, shown = kb.weekly_auto(s, datetime(2026, 10, 26, 9, 30))
    assert spoken.startswith("Sir, your weekly report. Week of 19 October") and shown.startswith("Weekly report.")
    assert kb.weekly_auto(s, datetime(2026, 10, 26, 11, 0)) == ("", "")  # once a week
