"""Instagram comment replies: all HTTP is mocked, nothing reaches the network."""

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

import helpers
import instagram_comments as igc
import instagram_dms as ig
from config import Settings

TOKEN = "IGAAsecretTOKEN1234567890"
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
ME = {"id": "900", "user_id": "17840000000000001", "username": "kineticwebdesigns"}


def settings(**kw) -> Settings:
    return replace(Settings(), instagram_token=TOKEN, **kw)


def stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S+0000")


def comment(cid, text, who=("u1", "joe"), at=NOW - timedelta(minutes=5), replies=None):
    return {"id": cid, "text": text, "username": who[1], "from": {"id": who[0], "username": who[1]},
            "timestamp": stamp(at), "replies": {"data": replies or []}}


class FakeIG:
    """graph.instagram.com for one post with comments; records every write."""

    def __init__(self, comments, fail=False):
        self.comments, self.fail = comments, fail
        self.public, self.private, self.requests = [], [], []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/refresh_access_token"):
            return httpx.Response(400, json={"error": {"message": "too new"}})
        if path.endswith("/me/media"):
            return httpx.Response(200, json={"data": [{"id": "p1", "comments_count": len(self.comments)}]})
        if path.endswith("/p1/comments"):
            return httpx.Response(200, json={"data": self.comments})
        if path.endswith("/replies"):
            if self.fail:
                return httpx.Response(400, json={"error": {"message": f"nope {TOKEN}"}})
            self.public.append((path.split("/")[-2], request.url.params["message"]))
            return httpx.Response(200, json={"id": f"r{len(self.public)}"})
        if path.endswith("/me/messages"):
            body = json.loads(request.content)
            self.private.append(body)
            return httpx.Response(200, json={"message_id": f"m{len(self.private)}"})
        if path.endswith("/me"):
            return httpx.Response(200, json=ME)
        return httpx.Response(404, json={"error": {"message": "unknown"}})

    def client(self):
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))


class FakeAI:
    def __init__(self, answer: dict):
        self.answer, self.calls = answer, []
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(self.answer))])


@pytest.fixture(autouse=True)
def no_ai(monkeypatch):
    monkeypatch.setattr(helpers, "_client", None)


async def run(fake, s=None, announce=None):
    async with fake.client() as http:
        return await igc.poll(s or settings(), http, announce, now=NOW)


async def started(fake, s=None):
    """A first run (marks what's there as seen), then the new comments are added by the test."""
    first = fake.comments
    fake.comments = []
    await run(fake, s)
    fake.comments = first


async def test_first_run_answers_nothing():
    fake = FakeIG([comment("c1", "SITE")])
    out = await run(fake)
    assert out["first_run"] is True and fake.public == [] and fake.private == []
    await run(fake)
    assert fake.public == [] and fake.private == []


async def test_interest_gets_public_reply_and_private_dm(monkeypatch):
    fake = FakeIG([comment("c1", "SITE")])
    await started(fake)
    ai = FakeAI({"action": "reply", "reason": "", "reply": "Our Starter site is £395 and you see a free mock-up "
                 "first. What's your business called?", "business_name": "", "website": ""})
    monkeypatch.setattr(helpers, "_client", ai)
    out = await run(fake)
    assert out["private"] == 1 and out["public"] == 1
    assert fake.private[0]["recipient"] == {"comment_id": "c1"}
    assert fake.private[0]["message"]["text"].endswith(ig.SIGN_OFF)
    assert fake.public == [("c1", igc.PUBLIC_DM)]
    assert "comment on our Instagram post" in ai.calls[0]["messages"][0]["content"]
    for r in fake.requests:  # token only ever in the header
        assert TOKEN not in str(r.url)
    await run(fake)  # handled once
    assert len(fake.public) == 1 and len(fake.private) == 1


async def test_compliment_gets_thanks_only():
    fake = FakeIG([comment("c1", "🔥🔥 love this")])
    await started(fake)
    out = await run(fake)
    assert fake.public == [("c1", igc.PUBLIC_THANKS)] and fake.private == [] and out["public"] == 1


async def test_no_ai_sends_holding_dm_with_link():
    fake = FakeIG([comment("c1", "how much for a website?")])
    await started(fake)
    await run(fake)
    assert fake.private[0]["message"]["text"] == ig.NO_AI
    assert fake.public == [("c1", igc.PUBLIC_DM)]


async def test_abuse_and_complaints_go_to_owner_without_reply():
    fake = FakeIG([comment("c1", "you lot are scammers"), comment("c2", "I want a refund")])
    await started(fake)
    told = []

    async def announce(text, kind):
        told.append(text)

    out = await run(fake, announce=announce)
    assert fake.public == [] and fake.private == [] and out["handed_off"] == 2
    needs = ig.load_state(settings())["needs_you"]
    assert {n["thread"] for n in needs} == {"comment:c1", "comment:c2"}
    assert len(told) == 2


async def test_never_answers_ourselves_answered_or_old_comments():
    ours = {"id": "x", "username": "kineticwebdesigns", "from": {"id": ME["user_id"], "username": ME["username"]}}
    fake = FakeIG([comment("c1", "nice", who=(ME["user_id"], ME["username"])),
                   comment("c2", "SITE", replies=[ours]),
                   comment("c3", "SITE", at=NOW - timedelta(days=8))])
    await started(fake)
    await run(fake)
    assert fake.public == [] and fake.private == []


async def test_paused_or_switched_off_sends_nothing():
    fake = FakeIG([comment("c1", "SITE")])
    await started(fake)
    s = ig.load_state(settings())
    s["paused"] = True
    ig.save_state(settings(), s)
    await run(fake)
    assert fake.public == [] and fake.private == []
    assert ig.load_state(settings())["needs_you"][0]["thread"] == "comment:c1"
    fake2 = FakeIG([comment("c9", "SITE")])
    out = await run(fake2, settings(instagram_comments=False))
    assert out == {"skipped": "off"} and fake2.requests == []


async def test_refused_reply_is_not_retried_and_token_never_leaks(capsys):
    fake = FakeIG([comment("c1", "🔥")], fail=True)
    await started(fake)
    await run(fake)
    s = igc.load_state(settings())
    assert "c1" in s["seen"] and TOKEN not in s.get("last_error", "")
    assert TOKEN not in capsys.readouterr().out
    await run(fake)  # not retried
    assert len([r for r in fake.requests if r.url.path.endswith("/replies")]) == 1


async def test_rate_limit_per_poll():
    fake = FakeIG([comment(f"c{i}", "great work") for i in range(15)])
    await started(fake)
    out = await run(fake)
    assert out["public"] == igc.MAX_ACTIONS_PER_POLL
    out = await run(fake)
    assert out["public"] == 5


def test_status_mentions_comments():
    assert "Comments:" in ig.status(settings(), {})
