import asyncio
import json

import pytest

import alerts
import tools
from brain import Brain, request_options
from config import Settings
from tests.test_brain import FakeClient, reply, run, text

SETTINGS = Settings(model="claude-opus-5", tasks_file="", enable_screen=False, user_address="sir",
                    email_address="me@gmail.com", email_app_password="abcd efgh", email_check_seconds=0)


@pytest.mark.parametrize(
    "sender, subject, service",
    [
        ("Deliveroo <noreply@t.deliveroo.com>", "Your order is on its way", "Deliveroo"),
        ("Just Eat <orders@just-eat.co.uk>", "Order confirmed: Pizza Palace", "Just Eat"),
        ("Uber Receipts <noreply@uber.com>", "Your Friday evening order with Uber Eats", "Uber Eats"),
        ("Amazon.co.uk <shipment-tracking@amazon.co.uk>", "Dispatched: 2 items", "Amazon"),
        ("Evri <noreply@evri.com>", "Your parcel is out for delivery today", "Evri"),
        ("Deliveroo <noreply@t.deliveroo.com>", "50% off your next order", None),  # advert
        ("Just Eat <news@just-eat.co.uk>", "Free delivery this weekend", None),  # advert
        ("Uber Receipts <noreply@uber.com>", "Your Friday trip with Uber", None),  # a ride, not food
        ("Mum <mum@example.com>", "Did your order arrive?", None),  # not a delivery company
    ],
)
def test_delivery_service(sender, subject, service):
    assert alerts.delivery_service(sender, subject) == service


def test_email_line():
    mail = alerts.Mail(1, "Deliveroo <noreply@deliveroo.com>", "Your rider is nearby.", None)
    assert alerts.email_line(SETTINGS, mail) == "Sir, an email from Deliveroo: Your rider is nearby."


@pytest.mark.parametrize(
    "app, texts, said",
    [
        ("Phone Link", ["Mum", "Incoming call"], "Sir, incoming call from Mum."),
        ("Phone Link", ["Incoming call", "+44 7700 900123"], "Sir, incoming call from +44 7700 900123."),
        ("Phone Link", ["Incoming call"], "Sir, you have an incoming call."),
        ("Phone Link", ["Deliveroo", "Your rider is 2 minutes away"], "Sir, Deliveroo: Your rider is 2 minutes away."),
        ("Phone Link", ["Uber Eats", "Your order has arrived."], "Sir, Uber Eats: Your order has arrived."),
        ("Phone Link", ["WhatsApp", "Dan: hi"], None),
        ("Teams", ["Incoming call", "Boss"], None),  # only calls from the phone
    ],
)
def test_call_line(app, texts, said):
    assert alerts.call_line(SETTINGS, app, texts) == said


class FakeIMAP:
    """Stands in for imaplib.IMAP4_SSL with a fixed inbox of (uid, from, subject)."""

    inbox: list = []
    readonly = None

    def __init__(self, host):
        self.host = host

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        assert password == "abcdefgh"  # spaces from Google's display are removed

    def select(self, box, readonly=False):
        FakeIMAP.readonly = readonly

    def uid(self, command, *args):
        if command == "search":
            return "OK", [" ".join(str(u) for u, *_ in self.inbox).encode()]
        wanted = {int(u) for u in args[0].split(",")}
        data = []
        for u, sender, subject in self.inbox:
            if u in wanted:
                head = f"From: {sender}\r\nSubject: {subject}\r\nDate: Sun, 27 Sep 2026 13:00:00 +0100\r\n\r\n"
                data += [(f"{u} (UID {u} BODY[HEADER.FIELDS (FROM SUBJECT DATE)] {{99}}".encode(), head.encode()), b")"]
        return "OK", data


@pytest.fixture
def inbox(monkeypatch):
    FakeIMAP.inbox = [
        (5, "Evri <noreply@evri.com>", "Your parcel is out for delivery"),
        (6, "Mum <mum@example.com>", "Sunday lunch"),
    ]
    monkeypatch.setattr(alerts.imaplib, "IMAP4_SSL", FakeIMAP)
    return FakeIMAP.inbox


def test_fetch_mail_is_read_only_and_skips_seen(inbox):
    mails = alerts.fetch_mail(SETTINGS, after_uid=5)
    assert FakeIMAP.readonly is True
    assert [(m.uid, m.subject) for m in mails] == [(6, "Sunday lunch")]
    assert mails[0].date is not None


def test_recent_deliveries_lists_only_deliveries(inbox):
    out = alerts.recent_deliveries(SETTINGS)
    assert "Evri: Your parcel is out for delivery" in out
    assert "Sunday lunch" not in out


async def test_watch_email_announces_only_new_deliveries(inbox):
    said = []

    async def announce(t):
        said.append(t)
        if len(said) == 1:
            raise asyncio.CancelledError  # stop the loop after the first announcement

    task = asyncio.create_task(alerts.watch_email(SETTINGS, announce))
    await asyncio.sleep(0.05)  # first look: existing mail is not read out
    assert said == []
    inbox.append((7, "Deliveroo <noreply@deliveroo.com>", "Your order is on its way"))
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 2)
    assert said == ["Sir, an email from Deliveroo: Your order is on its way."]


def test_check_deliveries_tool_only_with_email():
    names = lambda s: [t["name"] for t in tools.client_tool_definitions(s)]
    assert "check_deliveries" in names(SETTINGS)
    assert "check_deliveries" not in names(Settings(email_address="", email_app_password=""))
    assert "check_deliveries" in request_options(SETTINGS)["system"]


async def test_announcements_reach_the_next_turn():
    client = FakeClient(reply("end_turn", text("That was your mother, sir.")))
    b = Brain(SETTINGS, client, http=None)
    b.note("Sir, incoming call from Mum.")

    await run(b, "Who was that?")

    first = client.requests[0]["messages"][0]["content"]
    assert "incoming call from Mum" in first and first.endswith("Who was that?")
    assert b._notes == []


def test_server_says_announcements_on_open_pages(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    from fastapi.testclient import TestClient

    import server

    with TestClient(server.app) as client:
        with client.websocket_connect("/ws", headers={"origin": "http://testserver"}) as ws:
            client.portal.call(server.announce, server.app, "Sir, incoming call from Mum.")
            msg = ws.receive_json()
            assert msg["type"] == "say" and msg["text"] == "Sir, incoming call from Mum."
        assert server.app.state.pages == {}


@pytest.mark.parametrize(
    "event, said",
    [
        ({"event": "message", "message": "Incoming call from Mum"}, "Sir, incoming call from Mum."),
        ({"event": "message", "title": "Deliveroo", "message": "Your rider is nearby."}, "Sir, Deliveroo: Your rider is nearby."),
        ({"event": "keepalive"}, None),
        ({"event": "message", "message": "  "}, None),
    ],
)
def test_relay_line(event, said):
    assert alerts.relay_line(SETTINGS, event) == said


async def test_watch_relay_announces_posted_calls():
    import httpx

    settings = Settings(user_address="sir", ntfy_topic="jarvis-secret", ntfy_server="https://ntfy.example/")
    seen_urls = []

    def handler(request):
        seen_urls.append(str(request.url))
        lines = [{"event": "open"}, {"event": "message", "message": "Incoming call from +44 7700 900123"}]
        return httpx.Response(200, text="\n".join(json.dumps(x) for x in lines) + "\n")

    said = []

    async def announce(t):
        said.append(t)
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(alerts.watch_relay(settings, announce, transport=httpx.MockTransport(handler)), 2)
    assert seen_urls == ["https://ntfy.example/jarvis-secret/json"]
    assert said == ["Sir, incoming call from +44 7700 900123."]
