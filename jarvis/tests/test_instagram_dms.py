"""Instagram DM auto-reply: all HTTP is mocked, nothing reaches the network."""

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

import helpers
import instagram_dms as ig
import kinetic_store as st
import memory
from config import Settings

TOKEN = "IGAAsecretTOKEN1234567890"
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
ME = {"id": "900", "user_id": "17840000000000001", "username": "kineticwebdesigns"}


def settings(**kw) -> Settings:
    return replace(Settings(), instagram_token=TOKEN, **kw)


def stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S+0000")


def msg(mid, text, frm, at):
    who = {"id": ME["user_id"], "username": ME["username"]} if frm == "us" else {"id": frm[0], "username": frm[1]}
    return {"id": mid, "from": who, "message": text, "created_time": stamp(at)}


class FakeIG:
    """A stand-in for graph.instagram.com that records every request."""

    def __init__(self, convs, refresh=None, fail_send=False):
        self.convs, self.refresh, self.fail_send = convs, refresh, fail_send
        self.sent, self.requests = [], []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/refresh_access_token"):
            if self.refresh is None:
                return httpx.Response(400, json={"error": {"message": "Session has not been active long enough"}})
            return httpx.Response(200, json={"access_token": self.refresh, "token_type": "bearer",
                                             "expires_in": 5184000})
        if path.endswith("/me/messages"):
            if self.fail_send:
                return httpx.Response(400, json={"error": {"message": f"bad token {TOKEN}"}})
            body = json.loads(request.content)
            self.sent.append(body)
            return httpx.Response(200, json={"recipient_id": body["recipient"]["id"],
                                             "message_id": f"sent-{len(self.sent)}"})
        if path.endswith("/me/conversations"):
            return httpx.Response(200, json={"data": [
                {"id": cid, "messages": {"data": list(reversed(msgs))}} for cid, msgs in self.convs.items()]})
        if path.endswith("/me"):
            return httpx.Response(200, json=ME)
        return httpx.Response(404, json={"error": {"message": "unknown"}})

    def client(self):
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))


class FakeAI:
    def __init__(self, answer: dict | str):
        self.answer, self.calls = answer, []
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        text = self.answer if isinstance(self.answer, str) else json.dumps(self.answer)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


@pytest.fixture(autouse=True)
def no_ai(monkeypatch):
    monkeypatch.setattr(helpers, "_client", None)
    # a known token state: refreshed recently, so polls don't try to refresh unless a test says so
    st.save(Settings(), ig.TOKEN_FILE, {"token": TOKEN, "env": ig._fingerprint(TOKEN), "refreshed": 4e9})


async def run(fake: FakeIG, s=None, now=NOW, announce=None):
    async with fake.client() as http:
        return await ig.poll(s or settings(), http, announce, now=now)


async def test_first_run_marks_everything_seen_without_replying():
    fake = FakeIG({"c1": [msg("m1", "How much is a website?", ("u1", "joe"), NOW - timedelta(minutes=5))]})
    out = await run(fake)
    assert out["first_run"] is True
    assert fake.sent == []
    state = ig.load_state(settings())
    assert "m1" in state["seen"] and state["started"] is True
    out = await run(fake)  # same messages again: still nothing
    assert fake.sent == [] and out["first_run"] is False


async def test_replies_to_new_inbound_message_with_the_ai(monkeypatch):
    fake = FakeIG({"c1": [msg("m0", "hi", ("u1", "joe"), NOW - timedelta(hours=2))]})
    await run(fake)
    ai = FakeAI({"action": "reply", "reason": "", "reply": "Our Starter website is £395, and you see your design "
                 "before you pay anything. What's your business called?\n\nAlfred",
                 "business_name": "", "website": ""})
    monkeypatch.setattr(helpers, "_client", ai)
    fake.convs["c1"].append(msg("m1", "How much is a website?", ("u1", "joe"), NOW - timedelta(minutes=3)))
    out = await run(fake)
    assert out["replied"] == 1
    assert len(fake.sent) == 1
    sent = fake.sent[0]
    assert sent["recipient"] == {"id": "u1"}
    assert sent["message"]["text"].endswith(ig.SIGN_OFF)
    assert "\n\nAlfred\n" not in sent["message"]["text"]
    assert len(sent["message"]["text"]) <= ig.MAX_REPLY
    system = ai.calls[0]["system"]
    assert "£395" in system and "half when we start building" in system and "kineticwebdesigns.co.uk" in system
    log = (memory.root(settings()) / st.FOLDER / "Instagram" / "joe.md").read_text(encoding="utf-8")
    assert "How much is a website?" in log and "Alfred (auto)" in log
    # the token went only in the Authorization header
    for r in fake.requests:
        if "refresh_access_token" not in r.url.path:
            assert TOKEN not in str(r.url)
            assert r.headers["Authorization"] == f"Bearer {TOKEN}"
    # handled once: polling again sends nothing more
    await run(fake)
    assert len(fake.sent) == 1


async def test_never_replies_outside_24_hours_or_when_we_spoke_last(monkeypatch):
    fake = FakeIG({})
    await run(fake)  # first run with an empty inbox
    monkeypatch.setattr(helpers, "_client", FakeAI({"action": "reply", "reply": "Hello!"}))
    fake.convs = {
        "old": [msg("o1", "Hi, prices?", ("u2", "old_one"), NOW - timedelta(hours=25))],
        "ours": [msg("a1", "Hi", ("u3", "amy"), NOW - timedelta(hours=1)),
                 msg("a2", "Hello Amy!", "us", NOW - timedelta(minutes=30))],
    }
    out = await run(fake)
    assert fake.sent == [] and out["replied"] == 0


async def test_never_starts_a_conversation(monkeypatch):
    """A thread with only our own messages (or nobody else) never gets a message, and owner replies need an inbound."""
    fake = FakeIG({})
    await run(fake)
    monkeypatch.setattr(helpers, "_client", FakeAI({"action": "reply", "reply": "Hi!"}))
    fake.convs = {"c9": [msg("x1", "Hello from us", "us", NOW - timedelta(minutes=1))]}
    await run(fake)
    assert fake.sent == []
    async with fake.client() as http:
        with pytest.raises(ValueError):
            await ig.run_tool("instagram_dms", {"action": "reply", "thread": "nobody", "text": "hey",
                                                "confirmed": True}, settings(), http)
    assert fake.sent == []
    assert all(not r.url.path.endswith("/me/messages") for r in fake.requests)


async def test_handoff_sends_one_holding_reply_and_alerts_owner(monkeypatch):
    fake = FakeIG({"c1": [msg("m0", "hi", ("u1", "joe"), NOW - timedelta(hours=2))]})
    await run(fake)
    ai = FakeAI({"action": "reply", "reply": "should not be used"})
    monkeypatch.setattr(helpers, "_client", ai)
    alerts = []

    async def announce(text, kind):
        alerts.append((text, kind))

    fake.convs["c1"].append(msg("m1", "I want a refund, I'm making a complaint", ("u1", "joe"),
                                NOW - timedelta(minutes=2)))
    out = await run(fake, announce=announce)
    assert out["handed_off"] == 1
    assert [s["message"]["text"] for s in fake.sent] == [ig.HOLDING]
    assert ai.calls == []  # caught before the AI saw it
    assert alerts and "@joe" in alerts[0][0] and alerts[0][1] == "instagram"
    shown = ig.needs_you(settings(), {})
    assert "complaint" in shown and shown.card["title"] == ig.NEEDS_TITLE
    # a follow-up while it waits on the owner: no second holding reply, owner told again
    fake.convs["c1"].append(msg("m2", "Hello??", ("u1", "joe"), NOW - timedelta(minutes=1)))
    await run(fake, announce=announce)
    assert len(fake.sent) == 1 and len(alerts) == 2


async def test_ai_unsure_is_a_handoff(monkeypatch):
    fake = FakeIG({"c1": [msg("m0", "hi", ("u1", "joe"), NOW - timedelta(hours=2))]})
    await run(fake)
    monkeypatch.setattr(helpers, "_client", FakeAI({"action": "handoff", "reason": "unsure", "reply": ""}))
    fake.convs["c1"].append(msg("m1", "Can you do my tax return?", ("u1", "joe"), NOW - timedelta(minutes=2)))
    out = await run(fake)
    assert out["handed_off"] == 1 and fake.sent[0]["message"]["text"] == ig.HOLDING


async def test_reply_breaking_a_rule_is_not_sent(monkeypatch):
    fake = FakeIG({"c1": [msg("m0", "hi", ("u1", "joe"), NOW - timedelta(hours=2))]})
    await run(fake)
    monkeypatch.setattr(helpers, "_client", FakeAI({"action": "reply", "reply": "Sure, pay with Klarna!"}))
    fake.convs["c1"].append(msg("m1", "How do I pay?", ("u1", "joe"), NOW - timedelta(minutes=2)))
    await run(fake)
    assert [s["message"]["text"] for s in fake.sent] == [ig.HOLDING]


async def test_no_ai_sends_holding_reply_with_site_link_and_alerts():
    fake = FakeIG({"c1": [msg("m0", "hi", ("u1", "joe"), NOW - timedelta(hours=2))]})
    await run(fake)
    alerts = []

    async def announce(text, kind):
        alerts.append(text)

    fake.convs["c1"].append(msg("m1", "Do you make websites for cafes?", ("u1", "joe"), NOW - timedelta(minutes=2)))
    out = await run(fake, announce=announce)
    assert out["handed_off"] == 1
    text = fake.sent[0]["message"]["text"]
    assert text == ig.NO_AI and "https://kineticwebdesigns.co.uk" in text
    assert alerts


async def test_paused_notifies_without_replying(monkeypatch):
    fake = FakeIG({"c1": [msg("m0", "hi", ("u1", "joe"), NOW - timedelta(hours=2))]})
    await run(fake)
    assert "paused" in await ig.run_tool("instagram_dms", {"action": "pause"}, settings())
    fake.convs["c1"].append(msg("m1", "Prices?", ("u1", "joe"), NOW - timedelta(minutes=2)))
    out = await run(fake)
    assert fake.sent == [] and out["notified"] == 1
    assert "back on" in await ig.run_tool("instagram_dms", {"action": "resume"}, settings())


async def test_lead_capture_adds_prospect_marked_replied(monkeypatch):
    fake = FakeIG({"c1": [msg("m0", "hi", ("u1", "joe"), NOW - timedelta(hours=2))]})
    await run(fake)
    monkeypatch.setattr(helpers, "_client", FakeAI({
        "action": "reply", "reply": "Lovely! I'll make you a free home page mock-up.",
        "business_name": "Joe's Barbers", "website": "joesbarbers.co.uk"}))
    fake.convs["c1"].append(msg("m1", "It's Joe's Barbers, joesbarbers.co.uk", ("u1", "joe"),
                                NOW - timedelta(minutes=2)))
    await run(fake)
    p = next(r for r in st.rows_of(settings(), st.PROSPECTS) if r["name"] == "Joe's Barbers")
    assert p["source"] == "instagram" and p["website"] == "joesbarbers.co.uk"
    row = next(r for r in st.rows_of(settings(), st.OUTREACH) if r["name"] == "Joe's Barbers")
    assert row["status"] == "replied"


async def test_owner_reply_needs_confirmation(monkeypatch):
    fake = FakeIG({"c1": [msg("m0", "hi", ("u1", "joe"), datetime.now(timezone.utc) - timedelta(minutes=5))]})
    async with fake.client() as http:
        await ig.poll(settings(), http)
        said = await ig.run_tool("instagram_dms", {"action": "reply", "thread": "@joe", "text": "Hi Joe!"},
                                 settings(), http)
        assert "Not sent" in said and fake.sent == []
        said = await ig.run_tool("instagram_dms", {"action": "reply", "thread": "joe", "text": "Hi Joe!",
                                                   "confirmed": True}, settings(), http)
    assert "Sent" in said and fake.sent[0]["recipient"] == {"id": "u1"}
    assert fake.sent[0]["message"]["text"].endswith(ig.SIGN_OFF)


async def test_token_never_in_errors_or_logs(capsys):
    fake = FakeIG({"c1": [msg("m0", "hi", ("u1", "joe"), datetime.now(timezone.utc) - timedelta(minutes=5))]},
                  fail_send=True)
    async with fake.client() as http:
        await ig.poll(settings(), http)
        with pytest.raises(ValueError) as err:
            await ig.run_tool("instagram_dms", {"action": "reply", "thread": "joe", "text": "Hi",
                                                "confirmed": True}, settings(), http)
    assert TOKEN not in str(err.value) and "***" in str(err.value)

    def boom(request):
        raise httpx.ConnectError(f"failed for https://graph.instagram.com/?access_token={TOKEN}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(boom)) as http:
        with pytest.raises(ig.InstagramError) as err:
            await ig.poll(settings(), http)
        status = await ig.run_tool("instagram_dms", {"action": "status"}, settings(), http)
    assert TOKEN not in str(err.value) and TOKEN not in status
    assert TOKEN not in capsys.readouterr().out
    state = (memory.root(settings()) / ig.STATE).read_text(encoding="utf-8")
    assert TOKEN not in state
    assert ig.scrub(f"x?access_token={TOKEN}&y=1") == "x?access_token=***&y=1"


async def test_token_refresh_when_older_than_30_days():
    s = settings()
    st.save(s, ig.TOKEN_FILE, {"token": TOKEN, "env": ig._fingerprint(TOKEN), "refreshed": 1000.0})
    fake = FakeIG({}, refresh="IGAAnewTOKEN999")
    async with fake.client() as http:
        assert await ig.refresh_token(s, http, now=1000.0 + 31 * 86400) is True
        assert ig.current_token(s) == "IGAAnewTOKEN999"
        # not due again for 30 days
        assert await ig.refresh_token(s, http, now=1000.0 + 32 * 86400) is False
        assert (await ig.get_me(http, ig.current_token(s)))["username"] == ME["username"]
    calls = [r for r in fake.requests if r.url.path.endswith("/refresh_access_token")]
    assert len(calls) == 1 and calls[0].url.params["grant_type"] == "ig_refresh_token"
    assert all(r.headers.get("Authorization") == "Bearer IGAAnewTOKEN999" for r in fake.requests if r not in calls)
    # a different token pasted into .env wins over the stored refreshed one
    s2 = replace(Settings(), instagram_token="IGAAanotherFromEnv")
    assert ig.current_token(s2) == "IGAAanotherFromEnv"


async def test_failed_refresh_keeps_old_token_and_waits_a_day():
    s = settings()
    st.save(s, ig.TOKEN_FILE, {"token": TOKEN, "env": ig._fingerprint(TOKEN), "refreshed": 0})
    fake = FakeIG({}, refresh=None)
    async with fake.client() as http:
        assert await ig.refresh_token(s, http, now=5e6) is False
        assert await ig.refresh_token(s, http, now=5e6 + 3600) is False
    assert ig.current_token(s) == TOKEN
    assert len([r for r in fake.requests if "refresh" in r.url.path]) == 1
    assert TOKEN not in json.dumps(st.load(s, ig.STATE, {}))


def test_no_token_means_setup_message_and_no_watch():
    s = replace(Settings(), instagram_token="")
    assert "JARVIS_INSTAGRAM_TOKEN" in ig.status(s, {})


async def test_watch_returns_without_token():
    await ig.watch(replace(Settings(), instagram_token=""), None, None)


def test_tool_definition_is_registered():
    import tools
    assert ig in tools.ABILITIES
    names = [t["name"] for t in ig.tool_definitions()]
    assert names == ["instagram_dms"]
