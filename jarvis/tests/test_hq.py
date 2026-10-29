"""Kinetic HQ: the shared brain and the agents' schedules."""
from datetime import datetime, timedelta

from hq.agents import Agent, roster
from hq.brain import Brain


def test_brain_logs_facts_and_journal(tmp_path):
    b = Brain(tmp_path / "brain.db", journal_dir=tmp_path / "Journal")
    seen = []
    b.listen(seen.append)
    b.log("scout", "found 3 new leads", "win", {"new": 3})
    b.log("closer", "drafted", "nonsense-kind")
    b.set("leads.total", 3)
    assert b.get("leads.total") == 3 and b.get("missing", "x") == "x"
    ev = b.events()
    assert [e["agent"] for e in ev] == ["scout", "closer"] and ev[0]["data"] == {"new": 3}
    assert ev[1]["kind"] == "info"  # unknown kinds fall back to info
    assert b.count_today("scout", "win") == 1 and len(seen) == 2
    assert b.search("3 new")[0]["agent"] == "scout"
    journal = next((tmp_path / "Journal").glob("*.md")).read_text(encoding="utf-8")
    assert "**scout**: found 3 new leads" in journal


def test_runs_and_interval_schedule(tmp_path):
    b = Brain(tmp_path / "brain.db")
    a = Agent("guardian", "Sentinel", "Guardian", "x", "#fff", "job", every=5)
    now = datetime.now()
    assert a.due(b, now)
    rid = b.run_started("guardian")
    b.run_finished(rid, True, "ok")
    assert not a.due(b, now) and a.due(b, now + timedelta(minutes=6))
    assert b.runs_today("guardian") == 1 and b.last_run("guardian")["result"] == "ok"


def test_time_slots_run_once_per_slot(tmp_path):
    b = Brain(tmp_path / "brain.db")
    a = Agent("closer", "Blade", "Closer", "x", "#fff", "job", times=("09:05", "13:05"))
    day = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    assert not a.due(b, day)  # before the first slot
    nine = day.replace(hour=9, minute=10)
    assert a.due(b, nine)
    b.run_finished(b.run_started("closer"), True, "done")
    assert not a.due(b, datetime.now()) or datetime.now() >= day.replace(hour=13, minute=5)


def test_roster_has_nine_distinct_agents():
    keys = [a.key for a in roster()]
    assert len(keys) == len(set(keys)) == 9 and {"warden", "designer"} <= set(keys) and all(a.run for a in roster())


def test_vera_holds_back_bad_emails():
    from hq import outbox
    link = "https://kineticwebdesigns.co.uk/m/x/"
    good = ("Hi there,\n\nYour site doesn't work well on phones. So I made you this: a free example of a new home page. "
            f"You can open it on your phone here: {link}\n\nSee your design before you pay anything.\n\nWebsites start "
            "from £395, and you pay half when we start building and half once everything's complete.\n\nThanks,\n"
            "Alfred, Kinetic Web Designs\n\nIf you'd rather not hear from me, just reply 'no thanks' and I won't contact "
            "you again.")
    assert outbox.rule_check("I made this for X", good, link, True) == []
    bad = good.replace("See your design before you pay anything.", "Pay monthly with Klarna. [Your name]")
    problems = outbox.rule_check("I made this for X", bad, link, True)
    assert any("see your design" in p for p in problems) and any("Klarna" in p for p in problems)
    assert any("placeholder" in p for p in problems)
    assert outbox.pick_address(["noreply@shop.co.uk", "hello@shop.co.uk", "x@gmail.com"],
                               "https://www.shop.co.uk") == "hello@shop.co.uk"
    assert not outbox.good_address("logo@2x.png")


async def test_the_morning_list_uses_the_premium_designer(monkeypatch, tmp_path):
    import sys
    from config import ROOT
    from hq import outbox
    from hq.brain import Brain
    sys.path.insert(0, str(ROOT / "hq" / "premium"))
    import auto
    asked = []

    async def fake_make(business, settings, client, website="", instagram="", progress=print):
        asked.append((business, website, instagram))
        return {"link": "https://k.test/m/kamo-v3/", "issues": [], "audit": {"grade": "good", "score": 91}}
    monkeypatch.setattr(auto, "make", fake_make)

    class Ctx:
        settings = __import__("config").Settings()
        brain = Brain(tmp_path / "b.db", journal_dir=tmp_path / "j")
    p = {"id": 7, "name": "Kamo Barbers", "town": "Newcastle", "website": "https://kamo.test", "instagram": "@kamo"}
    assert await outbox.make_mockup(Ctx(), p) == "https://k.test/m/kamo-v3/"
    assert asked == [("Kamo Barbers, Newcastle", "https://kamo.test", "kamo")]
    assert Ctx.brain.get("strong_site.7") is True  # their own site already rates well: Blade puts them last


def test_an_instagram_profile_must_belong_to_the_business():
    from hq import outbox
    assert outbox.same_business("Fade Inn Salon (@fade_inn_salon) • Instagram", "fade_inn_salon", "FADE INN SALON")
    assert not outbox.same_business("Gabi (@gabi_6987) • Instagram photos and videos", "gabi_6987", "FADE INN SALON")
    assert outbox.same_business("KAMO (@kamo.barbersnewcastle)", "kamo.barbersnewcastle", "Kamo Barbers Newcastle")
    assert outbox.same_business("Capello Barbers (@capellobarbers)", "CAPELLOBARBERS", "Capello Barbershop Whitchurch Road")


def test_emails_keep_pace_with_the_daily_limit():
    from hq import outbox
    day = datetime(2026, 10, 28)
    assert outbox.on_pace(15, day.replace(hour=9, minute=0)) == 1
    assert outbox.on_pace(15, day.replace(hour=13, minute=0)) == 8  # halfway through the day, half the emails
    assert outbox.on_pace(15, day.replace(hour=17, minute=15)) == 15


def test_a_held_back_follow_up_no_longer_blocks_the_rest(tmp_path, monkeypatch):
    # 28 Oct 2026: one follow-up the editor kept holding back stopped every other email all day
    import asyncio
    from hq import agents, outbox
    b = Brain(tmp_path / "brain.db")
    ctx = agents.Ctx(None, b, None)
    rows = [{"name": "Stuck", "email": "a@stuck.com"}, {"name": "Fine", "email": "b@fine.com"},
            {"name": "Also", "email": "c@also.com"}]
    sent = []
    monkeypatch.setattr(outbox, "watch_replies", lambda c: [])
    monkeypatch.setattr(outbox, "in_hours", lambda now: True)
    monkeypatch.setattr(outbox, "uk_now", lambda: datetime(2026, 10, 28, 13, 0))
    monkeypatch.setattr(outbox, "sent_today", lambda c: len(sent))
    monkeypatch.setattr(agents, "_due_by_email", lambda s: [r for r in rows if r["name"] not in sent])
    monkeypatch.setattr(outbox, "follow_up_email", lambda s, name, link, updated=False: ("Following up", "body " + name))

    async def no_mockup(c, row):
        return ""
    monkeypatch.setattr(outbox, "refresh_mockup", no_mockup)

    async def vet(c, p, name, to, subject, body, link, first, row=None, updated=False):
        if name == "Stuck":
            return f"held back {name}"
        sent.append(name)
        return f"sent the follow-up to {name}"
    monkeypatch.setattr(agents, "_vet_and_send", vet)

    async def no_leads(c):
        return None
    monkeypatch.setattr(outbox, "check_companies", no_leads)
    monkeypatch.setattr(outbox, "candidates", lambda s, ltd: [])
    monkeypatch.setattr(outbox, "limited_companies", lambda brain: set())
    out = asyncio.run(agents.warden(ctx))
    assert sent == ["Fine", "Also"] and "sent the follow-up to Fine" in out  # behind pace at 13:00: two in one run
    assert b.get("held.a@stuck.com") == "2026-10-28"  # held for today, tried again tomorrow



def test_a_follow_up_with_an_updated_mock_up_says_so(monkeypatch):
    from hq import outbox
    import kinetic_outreach as tracker
    body = ("Hi there,\n\nI'm just following up.\n\nThe free example home page I made for you is still yours to see, "
            "with no obligation.\n\nThanks")
    monkeypatch.setattr(tracker, "follow_up_draft", lambda s, a: {"body": "Subject: Following up\n\n" + body})
    parts = outbox.follow_up_email(None, "Joe's", "https://x/m/joes-v2/", updated=True)[1].split("\n\n")
    assert parts[2].startswith("Since my last email I've made you a new, updated design for Joe's")
    assert parts[2].endswith("https://x/m/joes-v2/")
    assert outbox.follow_up_email(None, "Joe's", "https://x/m/joes/")[1].count("https://x/m/joes/") == 1
