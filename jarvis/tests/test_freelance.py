import asyncio
import json
from datetime import datetime, timedelta

import pytest

import freelance_clients
import freelance_docs
import freelance_money
import freelance_store as st
import freelance_work
import memory
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def cl(s, **a):
    return freelance_clients.run_tool("freelance_clients", a, s)


def wk(s, **a):
    return freelance_work.run_tool("freelance_work", a, s)


def mo(s, **a):
    return freelance_money.run_tool("freelance_money", a, s)


def dc(s, **a):
    return freelance_docs.run_tool("freelance_docs", a, s)


def dump(data):
    return json.dumps(data, ensure_ascii=False)


def kind(shown):
    assert isinstance(shown, screen.Shown)
    return shown.card["kind"]


def iso(days=0):
    return (st.today() + timedelta(days=days)).isoformat()


def test_registered_and_through_tools(s):
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"freelance_clients", "freelance_work", "freelance_money", "freelance_docs"} <= names
    assert {"freelance-board", "freelance-calc", "freelance-timesheet", "freelance-meter", "freelance-checklist"} <= screen.EXTRA_KINDS
    out = asyncio.run(tools._run_tool("freelance_money", {"action": "day_rate", "target_income": 40000}, s, None))
    assert kind(out) == "freelance-calc"


def test_every_action_is_handled_and_unknown_is_friendly(s):
    for mod, tool in ((freelance_clients, "freelance_clients"), (freelance_work, "freelance_work"),
                      (freelance_money, "freelance_money"), (freelance_docs, "freelance_docs")):
        enum = mod.tool_definitions()[0]["input_schema"]["properties"]["action"]["enum"]
        assert enum == mod.ACTIONS and len(set(enum)) == len(enum)
        with pytest.raises(ValueError):
            mod.run_tool(tool, {"action": "nope"}, s)


def test_clients_leads_and_pipeline(s):
    assert kind(cl(s, action="client_add", client="Acme Ltd", contact="sam@acme.example", work="logos", note="likes blue")) == "table"
    with pytest.raises(ValueError):
        cl(s, action="client_add", client="acme ltd")
    assert "Noted" in cl(s, action="client_note", client="acme", note="pays quickly")
    assert kind(cl(s, action="clients")) == "table"
    shown = cl(s, action="client_show", client="Acme")
    assert kind(shown) == "freelance-calc" and "pays quickly" in dump(shown.card["data"])
    assert kind(cl(s, action="lead_add", client="Zed", title="Website copy", value=400, source="referral")) == "freelance-board"
    assert kind(cl(s, action="lead_add", client="Acme Ltd", title="Brochure", value=900, source="upwork")) == "freelance-board"
    moved = cl(s, action="lead_move", lead_id=1, stage="proposal sent")
    assert kind(moved) == "freelance-board" and "follow-up" in moved
    cols = {c["stage"]: c for c in moved.card["data"]["columns"]}
    assert cols["proposal sent"]["count"] == 1 and cols["enquiry"]["count"] == 1
    assert kind(cl(s, action="pipeline")) == "freelance-board"
    with pytest.raises(ValueError):
        cl(s, action="win_rate")
    won = cl(s, action="lead_move", lead_id=1, stage="won")
    assert "client list" in won
    cl(s, action="lead_move", lead_id=2, stage="lost", reason="too expensive")
    rate = cl(s, action="win_rate")
    assert kind(rate) == "freelance-calc" and rate.card["data"]["headline"] == "50% won"
    assert "too expensive" in dump(rate.card["data"])
    with pytest.raises(ValueError):
        cl(s, action="lead_move", lead_id=1, stage="nonsense")


def test_followups(s):
    cl(s, action="lead_add", client="Zed", title="Logo", follow_up=iso(-1))
    listing = cl(s, action="lead_followups")
    assert kind(listing) == "list" and "Zed" in listing.card["items"][0]["label"]
    assert "again in a week" in cl(s, action="followed_up", client="Zed")
    assert cl(s, action="lead_followups") == "No leads need a follow-up."


def test_client_value_and_remove(s):
    with pytest.raises(ValueError):
        cl(s, action="client_value")
    cl(s, action="client_add", client="Acme")
    wk(s, action="project_add", project="Logo", client="Acme", fee=500, est_hours=10)
    wk(s, action="time_log", project="Logo", hours=5)
    value = cl(s, action="client_value")
    assert kind(value) == "table" and value.card["rows"][0][3] == "£100/h"
    assert "confirm" in cl(s, action="client_remove", client="Acme")
    assert cl(s, action="client_remove", client="Acme", confirmed=True) == "Removed Acme."
    assert st.clients(s) == []


def test_onboarding_offboarding_and_drafts(s):
    on = cl(s, action="onboarding", client="Acme", tick=2)
    assert kind(on) == "freelance-checklist" and on.card["data"]["done"] == 1
    assert cl(s, action="onboarding", client="Acme", untick=2).card["data"]["done"] == 0
    with pytest.raises(ValueError):
        cl(s, action="onboarding", client="Acme", tick=99)
    off = cl(s, action="offboarding", client="Acme", tick=1)
    assert off.card["data"]["total"] == len(freelance_clients.OFFBOARDING)
    for k in freelance_clients.DRAFTS:
        d = cl(s, action="feedback_draft", client="Acme", kind=k, project="the logo", my_name="Jo")
        assert kind(d) == "text" and "Nothing has been sent" in d and "Jo" in d.card["text"]
    assert list((memory.root(s) / "Freelance").glob("Testimonial request*.md"))


def test_testimonial_bank(s):
    with pytest.raises(ValueError):
        cl(s, action="testimonials")
    cl(s, action="testimonial_add", client="Acme", quote="Brilliant and quick.", permission=True)
    cl(s, action="testimonial_add", client="Zed", quote="Good.")
    assert len(cl(s, action="testimonials").card["rows"]) == 2
    only = cl(s, action="testimonials", approved_only=True)
    assert [r[1] for r in only.card["rows"]] == ["Acme"]


def test_projects_milestones_and_due(s):
    assert kind(wk(s, action="project_add", project="Website", client="Acme", due=iso(5), est_hours=20, fee=800)) == "table"
    assert kind(wk(s, action="projects")) == "table"
    ms = wk(s, action="milestone_add", project="Website", title="Wireframes", due=iso(2), amount=200)
    assert kind(ms) == "list"
    wk(s, action="milestone_add", project="Website", title="Build")
    assert kind(wk(s, action="milestones", project="Website")) == "list"
    due = wk(s, action="due_soon")
    assert kind(due) == "list" and len(due.card["items"]) == 2
    done = wk(s, action="milestone_done", project="Website", milestone="wire")
    assert "1 of 2" in done
    assert "0 of 2" in wk(s, action="milestone_done", project="Website", milestone="1", reopen=True)
    with pytest.raises(ValueError):
        wk(s, action="milestone_done", project="Website", milestone="nothing")
    upd = wk(s, action="project_update", project="Website", status="in review", note="waiting")
    assert kind(upd) == "table" and upd.card["rows"][0][3] == "in review"
    with pytest.raises(ValueError):
        wk(s, action="project_update", project="Website", status="bogus")
    wk(s, action="project_update", project="Website", status="done")
    assert wk(s, action="due_soon") == "Nothing freelance is due in that time."
    assert "confirm" in wk(s, action="project_remove", project="Website")
    assert wk(s, action="project_remove", project="Website", confirmed=True) == "Removed Website."


def test_timer_time_and_timesheet(s):
    wk(s, action="project_add", project="Logo", client="Acme")
    started = wk(s, action="timer_start", project="Logo")
    assert kind(started) == "timer" and "Acme" in started
    assert kind(wk(s, action="timer_status")) == "timer"
    data = st.time_data(s)
    data["running"]["started"] = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
    st.save(s, st.TIME, data)
    assert "Logged 2h 00m on Logo for Acme" in wk(s, action="timer_stop")
    assert wk(s, action="timer_stop") == "No freelance timer is running."
    assert wk(s, action="timer_status") == "No freelance timer is running."
    assert "Logged 1h 30m" in wk(s, action="time_log", client="Zed", project="Admin", hours=1.5, billable=False)
    sheet = wk(s, action="timesheet")
    assert kind(sheet) == "freelance-timesheet" and sheet.card["data"]["total"] == 3.5
    assert len(sheet.card["data"]["rows"]) == 2 and len(sheet.card["data"]["days"]) == 7
    with pytest.raises(ValueError):
        wk(s, action="timesheet", week="last")
    summary = wk(s, action="time_summary")
    assert kind(summary) == "table" and summary.card["rows"][0][:2] == ["Acme", "2"]


def test_timer_start_stops_the_old_timer(s):
    wk(s, action="timer_start", client="Acme", project="A")
    said = wk(s, action="timer_start", client="Zed", project="B")
    assert "Stopped A" in said and len(st.time_data(s)["entries"]) == 1


def test_unbilled_and_mark_billed(s):
    assert wk(s, action="unbilled") == "All your logged time has been billed."
    wk(s, action="time_log", client="Acme", project="Logo", hours=4)
    wk(s, action="time_log", client="Acme", project="Admin", hours=1, billable=False)
    shown = wk(s, action="unbilled", rate=50)
    assert kind(shown) == "table" and shown.card["rows"][0][3] == "£200"
    assert "Marked 4h 00m" in wk(s, action="mark_billed", client="Acme", project="Logo")
    assert wk(s, action="mark_billed", client="Acme") == "Marked 1h 00m (1 entries) as billed."
    assert wk(s, action="mark_billed", client="Acme") == "There is no unbilled time for that."


def test_scope_creep_and_change_request(s):
    with pytest.raises(ValueError):
        wk(s, action="scope_list")
    shown = wk(s, action="scope_add", client="Acme", project="Website", request="Add a blog", extra_hours=4, rate=40)
    assert kind(shown) == "table" and shown.card["rows"][0][4] == "£160"
    draft = wk(s, action="change_request", scope_id=1, my_name="Jo")
    assert kind(draft) == "text" and "£160" in draft.card["text"] and "Nothing has been sent" in draft
    assert "now approved" in wk(s, action="scope_update", scope_id=1, status="approved")
    with pytest.raises(ValueError):
        wk(s, action="scope_update", scope_id=1, status="weird")
    with pytest.raises(ValueError):
        wk(s, action="change_request", scope_id=9)
    assert kind(wk(s, action="scope_list", project="Website")) == "table"


def test_retainers(s):
    with pytest.raises(ValueError):
        wk(s, action="retainers")
    shown = wk(s, action="retainer_add", client="Acme", hours_included=10, fee=600)
    assert kind(shown) == "freelance-meter"
    with pytest.raises(ValueError):
        wk(s, action="retainer_log", client="Nobody", hours=1)
    wk(s, action="retainer_log", client="acme", hours=4)
    row = wk(s, action="retainer_log", client="Acme", hours=8).card["data"]["rows"][0]
    assert row["used"] == 12 and "over" in row["text"]
    assert "over their hours" in wk(s, action="retainers")


def test_numbers_and_day_rate(s):
    with pytest.raises(ValueError):
        mo(s, action="day_rate")
    with pytest.raises(ValueError):
        mo(s, action="set_numbers")
    assert kind(mo(s, action="set_numbers", target_income=40000, overheads=2000, billable_pct=60, holiday_weeks=5)) == "freelance-calc"
    shown = mo(s, action="day_rate", save=True)
    # (52-5)*5 - 8 - 5 = 222 working days, 133.2 billable; 42000 / 133.2
    assert shown.card["data"]["headline"] == "£315 a day"
    assert st.profile(s)["hourly_rate"] == round(42000 / 133.2 / 7.5, 2)
    assert "promise" in shown
    with pytest.raises(ValueError):
        mo(s, action="day_rate", billable_pct=0)
    with pytest.raises(ValueError):
        mo(s, action="day_rate", holiday_weeks=52)


def test_project_price_and_options(s):
    with pytest.raises(ValueError):
        mo(s, action="project_price", hours=10)
    shown = mo(s, action="project_price", hours=10, hourly_rate=40, buffer_pct=25, costs=20)
    assert shown.card["data"]["headline"] == "£520"
    with_fee = mo(s, action="project_price", hours=10, hourly_rate=40, buffer_pct=0, fee_pct=20)
    assert with_fee.card["data"]["headline"] == "£500"
    opts = mo(s, action="price_options", price=400)
    assert kind(opts) == "freelance-calc" and opts.card["data"]["headline"] == "£300 / £400 / £540"
    with pytest.raises(ValueError):
        mo(s, action="price_options", price=400, tiers=["a", "b"])


def test_deposit_real_rate_and_rate_rise(s):
    sched = mo(s, action="deposit_schedule", total=1000, start="2026-10-01", terms_days=14)
    rows = sched.card["data"]["rows"]
    assert [r[0] for r in rows] == ["Deposit (30%)", "Milestone 1 (40%)", "Final payment (30%)"]
    assert "£400" in rows[1][1] and "15 Oct" in rows[2][1]
    with pytest.raises(ValueError):
        mo(s, action="deposit_schedule", total=1000, deposit_pct=70, final_pct=50)
    real = mo(s, action="real_rate", fee=500, hours=20, costs=50, hourly_rate=30)
    assert real.card["data"]["headline"] == "£22.50 an hour" and "25% below" in dump(real.card["data"])
    rise = mo(s, action="rate_rise", current_rate=40, rise_pct=10, hours_per_year=1000, my_name="Jo")
    assert rise.card["data"]["headline"] == "£44" and "£4,000" in dump(rise.card["data"]) and "nothing has been sent" in rise
    assert list((memory.root(s) / "Freelance").glob("Rate rise notice*.md"))


def test_billable_capacity_availability(s):
    with pytest.raises(ValueError):
        mo(s, action="billable_percent")
    wk(s, action="time_log", client="Acme", project="Logo", hours=15)
    wk(s, action="time_log", client="Acme", project="Admin", hours=5, billable=False)
    pct = mo(s, action="billable_percent")
    assert kind(pct) == "freelance-meter" and pct.card["data"]["rows"][0]["used"] == 15 and "40%" in pct
    wk(s, action="project_add", project="Site", client="Acme", est_hours=40, due=iso(14))
    cap = mo(s, action="capacity", hours_week=20, weeks=4, typical_hours=10, buffer_pct=0)
    # 80 hours minus 40 left on Site
    assert kind(cap) == "freelance-calc" and "4 more projects of 10" in cap
    week = mo(s, action="availability", hours_week=20, weeks=4)
    assert kind(week) == "freelance-meter" and len(week.card["data"]["rows"]) == 4
    assert week.card["data"]["rows"][0]["used"] > 0


def test_late_payment(s):
    interest = mo(s, action="late_interest", amount=1000, days_late=73, base_rate=4)
    # 1000 * 12% * 73/365 = 24; fixed £70
    assert kind(interest) == "freelance-calc" and interest.card["data"]["headline"] == "£94"
    assert "GOV.UK" in dump(interest.card["data"])
    small = mo(s, action="late_interest", amount=500, due_date=iso(-10), base_rate=4)
    assert "£40" in dump(small.card["data"])
    with pytest.raises(ValueError):
        mo(s, action="late_interest", amount=500, days_late=5)
    with pytest.raises(ValueError):
        mo(s, action="late_interest", amount=500, base_rate=4)
    text = mo(s, action="late_explainer")
    assert kind(text) == "text" and "GOV.UK" in text.card["text"]
    for tone in freelance_money.TONES:
        d = mo(s, action="late_draft", tone=tone, client="Zed", invoice_ref="INV-7", amount=250, due_date=iso(-12), my_name="Jo")
        assert kind(d) == "text" and "INV-7" in d.card["text"] and "£250" in d.card["text"]
    assert "Interest" in d.card["text"] or "interest" in d.card["text"]
    with pytest.raises(ValueError):
        mo(s, action="late_draft", tone="rude", client="Zed")


def test_proposal_case_study_and_terms(s):
    args = dict(client="Acme", title="Brand refresh", scope=["Logo", "Colours"], deliverables=["Logo files"], timeline=["Week 1: draft"],
                options=[{"name": "Basic", "price": 400, "includes": "1 logo"}, {"name": "Full", "price": 900}],
                exclusions=["Printing"], my_name="Jo")
    md = dc(s, action="proposal", **args)
    assert kind(md) == "file" and md.card["name"].endswith(".md") and "Nothing has been sent" in md
    text = (memory.root(s) / "Freelance" / md.card["name"]).read_text(encoding="utf-8")
    assert "| Basic | £400 | 1 logo |" in text and "## Terms" in text and "## Not included" in text
    html = dc(s, action="proposal", format="html", **{**args, "options": None, "price": 750, "title": "Brand <b>refresh</b>"})
    page = (memory.root(s) / "Freelance" / html.card["name"]).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in page and "£750" in page and "<b>" not in page
    with pytest.raises(ValueError):
        dc(s, action="proposal", client="Acme", title="X")
    case = dc(s, action="case_study", title="Cafe rebrand", problem="Menu was confusing", process=["Interviews", "Sketches"],
              result="Orders up", numbers=["12% more orders"], quote="Great", client="Cafe", tools=["Figma"])
    assert kind(case) == "file"
    assert "## The problem" in (memory.root(s) / "Freelance" / case.card["name"]).read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        dc(s, action="case_study", title="X", problem="p", result="r")
    terms = dc(s, action="terms_draft", deposit_pct=25, revision_rounds=3)
    body = (memory.root(s) / "Freelance" / terms.card["name"]).read_text(encoding="utf-8")
    assert "25% deposit" in body and "not legal advice" in body
    with pytest.raises(ValueError):
        dc(s, action="proposal", format="pdf", **args)


def test_kickoff_welcome_followup_bio(s):
    for service in freelance_docs.SERVICES:
        assert kind(dc(s, action="kickoff_questions", service=service)) == "text"
    with pytest.raises(ValueError):
        dc(s, action="kickoff_questions", service="plumbing")
    assert "Acme" in dc(s, action="welcome_draft", client="Acme", project="Logo", start="2026-10-12").card["text"]
    assert "proposal" in dc(s, action="proposal_followup", client="Acme").card["text"]
    bio = dc(s, action="profile_bio", service="video editing", audience="YouTubers", proof=["Edited 40 videos"])
    assert "Edited 40 videos" in bio.card["text"] and "honest" in bio.card["text"]


def test_platform_checklists_net_and_files(s):
    shown = dc(s, action="platform_checklist", platform="fiverr")
    assert kind(shown) == "freelance-checklist" and shown.card["data"]["done"] == 0
    assert dc(s, action="platform_tick", platform="fiverr", tick=1).card["data"]["done"] == 1
    assert dc(s, action="platform_checklist", platform="fiverr").card["data"]["done"] == 1
    assert dc(s, action="platform_checklist", platform="upwork").card["data"]["done"] == 0
    with pytest.raises(ValueError):
        dc(s, action="platform_tick", platform="fiverr")
    with pytest.raises(ValueError):
        dc(s, action="platform_checklist", platform="myspace")
    net = dc(s, action="platform_net", price=100, fee_pct=20, costs=5, hours=3)
    assert net.card["data"]["headline"] == "£75" and "£25" in dump(net.card["data"])
    assert "no freelance files" in dc(s, action="files")
    dc(s, action="terms_draft")
    files = dc(s, action="files")
    assert kind(files) == "list" and files.card["items"][0]["label"].startswith("Freelance terms")
