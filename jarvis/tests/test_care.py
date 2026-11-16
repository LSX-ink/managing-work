import asyncio
from hq.brain import Brain
from hq import care


def test_cancelled_plans_alert_once_and_block_changes(tmp_path, monkeypatch):
    # owner, 15 Nov 2026: "track which websites unsubscribes so we stop making changes for them"
    b = Brain(tmp_path / "brain.db")
    data = [{"id": "sub_1", "email": "bob@plumb.com", "name": "Bob", "website": "https://www.BobPlumbing.com/",
             "status": "canceled", "canceled_at": 1794784503000, "updated": 1},
            {"id": "sub_2", "email": "amy@sparks.com", "name": "Amy", "website": "amysparks.com", "status": "active",
             "cancel_at": 1797000000000, "updated": 2}]
    monkeypatch.setattr(care, "rows", lambda: data)
    sent = []

    async def push(s, text, kind):
        sent.append(text)
    out = asyncio.run(care.check(None, b, push))
    assert out == "1 care plans active, 1 cancelled"
    assert any("cancelled: Bob" in t for t in sent) and any("ending on" in t and "Amy" in t for t in sent)
    assert not care.may_change(b, "bobplumbing.com") and not care.may_change(b, "BOB@plumb.com")
    assert care.may_change(b, "amysparks.com")
    asyncio.run(care.check(None, b, push))
    assert len(sent) == 2  # no repeat alerts
    data[0]["status"] = "active"  # Bob rejoins
    asyncio.run(care.check(None, b, push))
    assert care.may_change(b, "bobplumbing.com")


def test_village_is_not_a_stay():
    from hq import outbox
    assert not outbox.stay({"name": "Village Plumbing, Air & Electric", "kind": "plumber"})
    assert outbox.stay({"name": "Sea View Villa", "kind": ""})
