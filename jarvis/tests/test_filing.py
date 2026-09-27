import asyncio
import email.utils
import json
from email.message import EmailMessage

import pytest

import filing
import memory
from config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(memory_dir=str(tmp_path / "memory"), email_address="me@example.com", email_app_password="x",
                    user_address="sir")


def payslip(sent="Sat, 27 Sep 2025 09:15:00 +0100", subject="Your Payslip", sender="VGC Payroll <pay@vgcgroup.co.uk>",
            msg_id="<a1@vgc>"):
    msg = EmailMessage()
    msg["From"], msg["Subject"], msg["Date"], msg["Message-ID"] = sender, subject, sent, msg_id
    msg.set_content("Please find your payslip attached.")
    msg.add_attachment(b"%PDF-1.4 payslip", maintype="application", subtype="pdf", filename="payslip_0927.pdf")
    return msg


def test_matches():
    rule = {"from": "VGC", "words": "payslip"}
    assert filing.matches(rule, "VGC Payroll <pay@vgc.co.uk>", "Your Payslip for September")
    assert filing.matches(rule, "vgc <x@y>", "Your pay slip")
    assert not filing.matches(rule, "VGC <x@y>", "Site induction")
    assert not filing.matches(rule, "Tesco <x@y>", "Your payslip")
    assert filing.matches({"from": "VGC", "words": ""}, "VGC <x@y>", "anything")


def test_add_rule_makes_the_folder(settings):
    rule = filing.add_rule(settings, "VGC", "payslip", "HS2", "VGC Payslip")
    assert rule == {"from": "VGC", "words": "payslip", "folder": "HS2", "name": "VGC Payslip"}
    assert (memory.root(settings) / "HS2").is_dir()
    filing.add_rule(settings, "vgc", "Payslip", "Work", "VGC Payslip")  # same rule again replaces it
    assert [r["folder"] for r in filing.rules(settings)] == ["Work"]
    assert filing.remove_rule(settings, "vgc") == 1 and filing.rules(settings) == []


def test_file_message_names_by_email_date(settings):
    rule = filing.add_rule(settings, "VGC", "payslip", "HS2", "VGC Payslip")
    saved = filing.file_message(settings, rule, payslip().as_bytes())
    assert sorted(p.name for p in saved) == ["VGC Payslip 2025-09-27.pdf", "VGC Payslip 2025-09-27.txt"]
    assert saved[0].read_bytes() == b"%PDF-1.4 payslip"
    assert "Please find your payslip" in (memory.root(settings) / "HS2" / "VGC Payslip 2025-09-27.txt").read_text()


class FakeIMAP:
    """Just enough IMAP for run_once: a readonly inbox of raw messages."""
    mails: list[bytes] = []

    def __init__(self, host):
        self.selected = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, user, password):
        pass

    def select(self, box, readonly=False):
        assert readonly, "filing must never change the inbox"

    def uid(self, command, *args):
        if command == "search":
            who = args[-1].strip('"').lower()
            hits = [str(i + 1).encode() for i, m in enumerate(self.mails)
                    if who in email.message_from_bytes(m)["From"].lower()]
            return "OK", [b" ".join(hits)]
        ids, what = args
        ids = ids if isinstance(ids, bytes) else ids.encode()
        assert b"PEEK" in what.encode(), "fetching must not mark mail as read"
        out = []
        for i in ids.split(b","):
            raw = self.mails[int(i) - 1]
            out.append((b"%s (UID %s BODY[] {1}" % (i, i), raw))
            out.append(b")")
        return "OK", out


def test_run_once_files_each_email_once(settings, monkeypatch):
    FakeIMAP.mails = [payslip().as_bytes(),
                      payslip(subject="Site induction", msg_id="<a2@vgc>").as_bytes(),
                      payslip(sent="Mon, 27 Oct 2025 09:00:00 +0000", msg_id="<a3@vgc>").as_bytes()]
    monkeypatch.setattr(filing.imaplib, "IMAP4_SSL", FakeIMAP)
    msg = asyncio.run(filing.run_tool("add_email_rule", {"sender": "VGC", "subject_words": "payslip", "folder": "HS2",
                                                          "name": "VGC Payslip"}, settings))
    assert "Filed 4 items" in msg
    names = sorted(p.name for p in (memory.root(settings) / "HS2").iterdir())
    assert names == ["VGC Payslip 2025-09-27.pdf", "VGC Payslip 2025-09-27.txt",
                     "VGC Payslip 2025-10-27.pdf", "VGC Payslip 2025-10-27.txt"]
    assert filing.run_once(settings, 400) == []  # already filed
    assert len(json.loads(filing.filed_path(settings).read_text())) == 2


def test_login_failure_is_explained(settings, monkeypatch):
    class Refused(FakeIMAP):
        def login(self, user, password):
            raise filing.imaplib.IMAP4.error("b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)'")
    monkeypatch.setattr(filing.imaplib, "IMAP4_SSL", Refused)
    msg = asyncio.run(filing.run_tool("add_email_rule", {"sender": "VGC", "folder": "HS2", "name": "VGC Payslip"}, settings))
    assert msg.startswith("Rule saved") and "refused the login" in msg and "app password" in msg
    assert filing.rules(settings)  # the rule is kept, and will file once the login works


def test_no_connection_is_explained(settings, monkeypatch):
    class Offline(FakeIMAP):
        def __init__(self, host):
            raise OSError("getaddrinfo failed")
    monkeypatch.setattr(filing.imaplib, "IMAP4_SSL", Offline)
    msg = asyncio.run(filing.run_tool("add_email_rule", {"sender": "VGC", "folder": "HS2", "name": "VGC Payslip"}, settings))
    assert "couldn't connect to imap.gmail.com" in msg


@pytest.mark.parametrize("address, host, expected", [
    ("me@gmail.com", "", "imap.gmail.com"),
    ("me@gmail.com", "  imap.gmail.com ", "imap.gmail.com"),
    ("me@gmail.com", "me@gmail.com", "imap.gmail.com"),
    ("me@hotmail.co.uk", "", "outlook.office365.com"),
    ("me@work.com", "mail.work.com", "mail.work.com"),
])
def test_imap_host_is_fixed_up(address, host, expected):
    assert Settings(email_address=address, email_imap_host=host).email_imap_host == expected


def test_app_password_spaces_are_removed(monkeypatch):
    import importlib
    import config
    monkeypatch.setenv("JARVIS_EMAIL_APP_PASSWORD", " abcd efgh ijkl mnop ")
    assert importlib.reload(config).Settings().email_app_password == "abcdefghijklmnop"
    monkeypatch.delenv("JARVIS_EMAIL_APP_PASSWORD")
    importlib.reload(config)
