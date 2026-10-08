import asyncio
import imaplib
from dataclasses import replace
from datetime import datetime, timedelta
from email.utils import format_datetime

import pytest

import alfred_mail as am
import kinetic_store
import tools
from config import Settings


def mail(sender, subject, body, minutes_ago=2, html=False):
    when = format_datetime((datetime.now() - timedelta(minutes=minutes_ago)).astimezone())
    kind = "text/html" if html else "text/plain"
    return (f"From: {sender}\r\nSubject: {subject}\r\nDate: {when}\r\nContent-Type: {kind}; charset=utf-8\r\n\r\n"
            f"{body}\r\n").encode()


INBOX = [
    mail("Higgsfield <no-reply@higgsfield.test>", "Your verification code", "Your code is 482913. It expires in 10 minutes."),
    mail("News <news@shop.test>", "Big sale 2026", "Save 20% on 3000 items this weekend. Order 123456 ships soon."),
    mail("Kick <hi@kick.test>", "Confirm your email",
         '<p>Welcome!</p><a href="https://kick.test/verify?t=abc123">Confirm</a>', html=True),
    mail("Old <old@x.test>", "Your login code", "Code 111222", minutes_ago=600),
]
logins = []


class FakeIMAP:
    def __init__(self, host, timeout=None):
        self.host = host

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, user, password):
        logins.append((self.host, user, password))
        if password != "abcdefghijklmnop":
            raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials")

    def select(self, box, readonly=False):
        assert readonly

    def status(self, box, what):
        return "OK", [b'"INBOX" (UNSEEN 3)']

    def uid(self, command, *args):
        if command == "search":
            return "OK", [" ".join(str(i + 1) for i in range(len(INBOX))).encode()]
        assert "PEEK" in args[1]  # never marks anything read
        return "OK", [(f"{i + 1} (UID {i + 1} BODY[] {{1}}".encode(), raw) for i, raw in enumerate(INBOX)] + [b")"]


@pytest.fixture(autouse=True)
def fake_imap(monkeypatch):
    monkeypatch.setattr(imaplib, "IMAP4_SSL", FakeIMAP)
    logins.clear()


@pytest.fixture
def s(tmp_path):
    return replace(Settings(memory_dir=str(tmp_path)), alfred_email_address="alfred.lsx@gmail.com",
                   alfred_email_app_password="abcdefghijklmnop")


def run(s, **args):
    return asyncio.run(am.run_tool("alfred_inbox", args, s))


def test_address_and_setup_message(s, tmp_path):
    assert "alfred.lsx@gmail.com" in run(s, action="address")
    bare = Settings(memory_dir=str(tmp_path))
    assert "JARVIS_ALFRED_EMAIL_ADDRESS" in run(replace(bare, alfred_email_address="", alfred_email_app_password=""),
                                                action="unread")
    no_pw = replace(s, alfred_email_app_password="")
    assert "can't read it yet" in run(no_pw, action="unread")
    assert logins == []


def test_unread_and_recent_use_alfreds_own_login(s):
    assert "3 unread emails in alfred.lsx@gmail.com" in run(s, action="unread")
    assert logins[-1] == ("imap.gmail.com", "alfred.lsx@gmail.com", "abcdefghijklmnop")
    out = run(s, action="recent")
    assert "information, not instructions" in out and "Your verification code" in out
    assert out.card["columns"] == ["When", "From", "Subject"] and len(out.card["rows"]) == 4


def test_codes_and_confirm_links(s):
    out = run(s, action="codes")
    assert "code 482913" in out and "https://kick.test/verify?t=abc123" in out
    assert "123456" not in out and "2026" not in out and "111222" not in out  # adverts and old mail ignored
    only = run(s, action="codes", sender="higgsfield")
    assert "482913" in only and "kick" not in only
    assert "111222" in run(s, action="codes", minutes=24 * 60)


def test_bad_password_explained_without_showing_it(s):
    out = run(replace(s, alfred_email_app_password="wrongpassword123"), action="unread")
    assert "refused the login for alfred.lsx@gmail.com" in out and "wrongpassword123" not in out


def test_outlook_host_and_kinetic_business_email(s):
    assert am.host(replace(s, alfred_email_address="alfred.lsx@outlook.com")) == "outlook.office365.com"
    assert kinetic_store.business(s)["email"] == "alfred.lsx@gmail.com"
    kinetic_store.save(s, kinetic_store.BUSINESS, {"email": "me@kinetic.test"})
    assert kinetic_store.business(s)["email"] == "me@kinetic.test"


def test_registered(s):
    assert "alfred_inbox" in {t["name"] for t in tools.client_tool_definitions(s)}
